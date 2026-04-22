from collections import Counter, defaultdict
from datetime import timedelta
from decimal import Decimal, ROUND_HALF_UP

from django.db.models import Count, Q
from django.utils import timezone

from apps.booking.models import Booking
from apps.fuel.models import FuelReading, TelemetrySnapshot
from apps.fuel.services import generate_operational_alerts
from apps.routing.models import Bus, Trip, TripBusAssignment


RECENT_WINDOW_DAYS = 7
EXTENDED_WINDOW_DAYS = 30
ON_TIME_DELAY_THRESHOLD = 5
TELEMETRY_RESOLUTION_THRESHOLD = 15


def _format_percentage(numerator, denominator):
    if not denominator:
        return "0%"
    percentage = (Decimal(str(numerator)) / Decimal(str(denominator))) * Decimal("100")
    return f"{percentage.quantize(Decimal('0.1'), rounding=ROUND_HALF_UP)}%"


def _format_decimal(value, suffix=""):
    quantized = Decimal(str(value)).quantize(Decimal("0.1"), rounding=ROUND_HALF_UP)
    return f"{quantized}{suffix}"


def _get_assignment_queryset(window_start):
    return (
        TripBusAssignment.objects.select_related(
            "bus",
            "driver",
            "trip__schedule_slot__route__group__section",
        )
        .annotate(
            confirmed_bookings=Count(
                "bookings",
                filter=Q(bookings__status=Booking.STATUS_CONFIRMED),
                distinct=True,
            )
        )
        .filter(trip__service_date__gte=window_start.date())
    )


def _build_latest_telemetry_lookup(assignment_ids):
    latest = {}
    telemetry_by_assignment = defaultdict(list)
    telemetry_items = TelemetrySnapshot.objects.filter(assignment_id__in=assignment_ids).order_by("assignment_id", "-reported_at", "-id")
    for telemetry in telemetry_items:
        telemetry_by_assignment[telemetry.assignment_id].append(telemetry)
        latest.setdefault(telemetry.assignment_id, telemetry)
    return latest, telemetry_by_assignment


def _build_fuel_lookup(assignment_ids):
    latest = {}
    fuel_by_assignment = defaultdict(list)
    readings = FuelReading.objects.filter(assignment_id__in=assignment_ids).order_by("assignment_id", "-reported_at", "-id")
    for reading in readings:
        fuel_by_assignment[reading.assignment_id].append(reading)
        latest.setdefault(reading.assignment_id, reading)
    return latest, fuel_by_assignment


def _compute_occupancy(assignments):
    total_capacity = sum(assignment.bus.seat_capacity for assignment in assignments)
    total_bookings = sum(assignment.confirmed_bookings for assignment in assignments)
    busiest_assignment = max(assignments, key=lambda item: item.confirmed_bookings, default=None)
    detail = "No assigned trip capacity is available yet."
    if busiest_assignment:
        detail = (
            f"{busiest_assignment.trip.route_label} is carrying the strongest load at "
            f"{busiest_assignment.confirmed_bookings}/{busiest_assignment.bus.seat_capacity} booked seats."
        )
    return {
        "label": "Avg Occupancy",
        "value": _format_percentage(total_bookings, total_capacity),
        "detail": detail,
    }


def _compute_on_time_rate(assignments, latest_telemetry):
    tracked_assignments = [assignment for assignment in assignments if assignment.id in latest_telemetry]
    on_time_count = sum(
        1
        for assignment in tracked_assignments
        if latest_telemetry[assignment.id].delay_minutes <= ON_TIME_DELAY_THRESHOLD
    )
    if tracked_assignments:
        delayed = max(
            tracked_assignments,
            key=lambda item: latest_telemetry[item.id].delay_minutes,
        )
        detail = (
            f"Based on latest telemetry delays across {len(tracked_assignments)} tracked trips; "
            f"{delayed.trip.route_label} is currently the most delayed."
        )
    else:
        detail = "No telemetry-backed trips are available yet, so this uses a safe zero baseline."
    return {
        "label": "On-Time Rate",
        "value": _format_percentage(on_time_count, len(tracked_assignments)),
        "detail": detail,
        "approximate": True,
    }


def _compute_alert_resolution(telemetry_by_assignment):
    restored_gaps = []
    for telemetry_items in telemetry_by_assignment.values():
        ordered_items = list(reversed(telemetry_items))
        for previous, current in zip(ordered_items, ordered_items[1:]):
            gap_minutes = max(0, int((current.reported_at - previous.reported_at).total_seconds() // 60))
            if current.is_online and gap_minutes >= TELEMETRY_RESOLUTION_THRESHOLD:
                restored_gaps.append(gap_minutes)

    average_gap = (sum(restored_gaps) / len(restored_gaps)) if restored_gaps else 0
    detail = (
        f"Computed from {len(restored_gaps)} resolved telemetry interruption window"
        f"{'' if len(restored_gaps) == 1 else 's'}."
    )
    if not restored_gaps:
        detail = "No resolved telemetry interruptions are available yet, so recovery time is waiting on real events."
    return {
        "label": "Alert Resolution",
        "value": f"{int(round(average_gap))} min",
        "detail": detail,
        "approximate": True,
    }


def _build_route_demand_signal(assignments):
    ranked = sorted(assignments, key=lambda item: item.confirmed_bookings, reverse=True)
    top_assignment = ranked[0] if ranked else None
    if not top_assignment:
        return {
            "title": "Route Demand",
            "value": "No demand yet",
            "detail": "Confirmed booking volume will appear here once trips begin accumulating bookings.",
        }

    return {
        "title": "Route Demand",
        "value": f"{top_assignment.confirmed_bookings} bookings",
        "detail": (
            f"{top_assignment.trip.route_label} is currently the busiest route in the reporting window, "
            f"led by bus {top_assignment.bus.code}."
        ),
    }


def _build_fuel_efficiency_signal(fuel_by_assignment):
    readings = [reading for items in fuel_by_assignment.values() for reading in items]
    if not readings:
        return {
            "title": "Fuel Efficiency",
            "value": "No readings",
            "detail": "Fuel efficiency will become visible once fuel readings are recorded for assigned trips.",
        }

    expected_total = sum(reading.expected_liters for reading in readings)
    actual_total = sum(reading.actual_liters for reading in readings)
    adherence = (actual_total / expected_total * Decimal("100")) if expected_total else Decimal("0")
    worst_reading = max(readings, key=lambda item: item.variance_percent)
    return {
        "title": "Fuel Efficiency",
        "value": f"{_format_decimal(adherence, '%')} of plan",
        "detail": (
            f"Fleet fuel use is tracking against expected liters from real readings; "
            f"{worst_reading.assignment.bus.code} shows the highest variance at {worst_reading.variance_percent}%."
        ),
    }


def _build_operational_risk_signal(alerts):
    if not alerts:
        return {
            "title": "Operational Risk",
            "value": "Calm",
            "detail": "No live alerts are currently being generated from trips, telemetry, fuel, or booking pressure.",
        }

    weighted_risk = sum(
        3 if alert.severity == "critical" else 2 if alert.severity == "warning" else 1
        for alert in alerts
    )
    risky_route = Counter(alert.route_label for alert in alerts if alert.route_label and alert.route_label != "System").most_common(1)
    risk_route_text = risky_route[0][0] if risky_route else "Fleet overview"
    return {
        "title": "Operational Risk",
        "value": f"{weighted_risk} risk pts",
        "detail": (
            f"{risk_route_text} is carrying the highest concentration of active monitoring pressure "
            f"from current alert signals."
        ),
    }


def _build_resource_balance_signal(total_buses, assignments, latest_telemetry):
    assigned_bus_ids = {assignment.bus_id for assignment in assignments}
    tracked_bus_ids = {assignment.bus_id for assignment in assignments if assignment.id in latest_telemetry}
    idle_count = max(total_buses - len(assigned_bus_ids), 0)
    return {
        "title": "Resource Balance",
        "value": f"{len(assigned_bus_ids)}/{total_buses} assigned",
        "detail": f"{idle_count} buses are currently idle, while {len(tracked_bus_ids)} assigned buses have telemetry coverage.",
    }


def _build_ridership_chart(assignments, window_start, now):
    daily_counts = {window_start.date() + timedelta(days=offset): 0 for offset in range((now.date() - window_start.date()).days + 1)}
    for assignment in assignments:
        daily_counts[assignment.trip.service_date] = daily_counts.get(assignment.trip.service_date, 0) + assignment.confirmed_bookings

    ordered_days = sorted(daily_counts.items())[-7:]
    labels = [service_date.strftime("%a") for service_date, _ in ordered_days]
    points = [count for _, count in ordered_days] or [0]
    peak_day = max(ordered_days, key=lambda item: item[1], default=None)
    detail = "Demand curve is based on confirmed bookings by trip service date."
    if peak_day:
        detail = f"Peak ridership landed on {peak_day[0].strftime('%A')} with {peak_day[1]} confirmed bookings."
    return {
        "eyebrow": "Ridership Pattern",
        "title": "Demand curve snapshot",
        "detail": detail,
        "labels": labels or ["Today"],
        "points": points,
    }


def _build_resource_chart(total_buses, active_assignments, scheduled_assignments, latest_telemetry):
    active_bus_ids = {assignment.bus_id for assignment in active_assignments}
    scheduled_bus_ids = {assignment.bus_id for assignment in scheduled_assignments}
    telemetry_online_ids = {
        assignment.bus_id
        for assignment in scheduled_assignments
        if assignment.id in latest_telemetry and latest_telemetry[assignment.id].is_online
    }
    inactive_buses = Bus.objects.filter(is_active=False).count()
    idle_count = max(total_buses - len(scheduled_bus_ids), 0)
    return {
        "eyebrow": "Resource Balance",
        "title": "Fleet allocation snapshot",
        "detail": "Live balance combines bus assignment state, telemetry coverage, and inactive fleet count.",
        "labels": ["Active", "Assigned", "Telemetry", "Idle", "Offline"],
        "points": [
            len(active_bus_ids),
            len(scheduled_bus_ids),
            len(telemetry_online_ids),
            idle_count,
            inactive_buses,
        ],
    }


def get_analytics_page_context(*, now=None):
    now = now or timezone.localtime()
    recent_window_start = now - timedelta(days=RECENT_WINDOW_DAYS)
    extended_window_start = now - timedelta(days=EXTENDED_WINDOW_DAYS)

    recent_assignments = list(_get_assignment_queryset(recent_window_start))
    extended_assignments = list(_get_assignment_queryset(extended_window_start))
    assignment_ids = [assignment.id for assignment in extended_assignments]

    latest_telemetry, telemetry_by_assignment = _build_latest_telemetry_lookup(assignment_ids)
    _, fuel_by_assignment = _build_fuel_lookup(assignment_ids)

    active_assignments = [
        assignment
        for assignment in recent_assignments
        if assignment.trip.get_effective_status(now) == Trip.STATUS_ACTIVE
    ]
    scheduled_assignments = [
        assignment
        for assignment in recent_assignments
        if assignment.trip.get_effective_status(now) in {Trip.STATUS_ACTIVE, Trip.STATUS_BOOKING_OPEN, Trip.STATUS_SCHEDULED}
    ]

    live_alerts = generate_operational_alerts(now=now)
    total_buses = Bus.objects.count()

    insight_cards = [
        _compute_occupancy(recent_assignments),
        _compute_on_time_rate(extended_assignments, latest_telemetry),
        _compute_alert_resolution(telemetry_by_assignment),
        {
            "label": "Fleet Utilization",
            "value": _format_percentage(len({assignment.bus_id for assignment in scheduled_assignments}), total_buses),
            "detail": f"{len({assignment.bus_id for assignment in active_assignments})} buses are active now, with {max(total_buses - len({assignment.bus_id for assignment in scheduled_assignments}), 0)} idle.",
        },
    ]

    insight_rows = [
        _build_route_demand_signal(extended_assignments),
        _build_fuel_efficiency_signal(fuel_by_assignment),
        _build_operational_risk_signal(live_alerts),
        _build_resource_balance_signal(total_buses, scheduled_assignments, latest_telemetry),
    ]

    return {
        "insight_cards": insight_cards,
        "insight_rows": insight_rows,
        "ridership_chart": _build_ridership_chart(extended_assignments, recent_window_start, now),
        "resource_chart": _build_resource_chart(total_buses, active_assignments, scheduled_assignments, latest_telemetry),
    }
