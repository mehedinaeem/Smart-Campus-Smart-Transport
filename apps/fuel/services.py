from collections import defaultdict
from dataclasses import dataclass
from datetime import timedelta
from decimal import Decimal

from django.db.models import Count, Q
from django.utils import timezone

from apps.booking.models import Booking
from apps.routing.models import Bus, Route, Trip, TripBusAssignment

from .models import FuelReading, TelemetrySnapshot


SEVERITY_CHOICES = [
    ("critical", "Critical"),
    ("warning", "Warning"),
    ("success", "Success"),
    ("info", "Info"),
]

ALERT_TYPE_CHOICES = [
    ("booking", "Booking"),
    ("fuel", "Fuel"),
    ("operations", "Operations"),
    ("schedule", "Schedule"),
    ("telemetry", "Telemetry"),
    ("traffic", "Traffic"),
]

STATUS_CHOICES = [
    ("active", "Active"),
    ("monitoring", "Monitoring"),
    ("resolved", "Resolved"),
]

SEVERITY_RANK = {
    "critical": 0,
    "warning": 1,
    "success": 2,
    "info": 3,
}

RECENT_COMPLETION_WINDOW_HOURS = 12
RECENT_TELEMETRY_MINUTES = 12
TELEMETRY_GAP_MINUTES = 15


@dataclass
class OperationalAlert:
    severity: str
    alert_type: str
    status: str
    title: str
    message: str
    timestamp: object
    route_id: int | None
    route_label: str
    bus_id: int | None
    bus_code: str
    trip_id: int | None
    trip_status: str

    @property
    def severity_label(self):
        return dict(SEVERITY_CHOICES)[self.severity]

    @property
    def alert_type_label(self):
        return dict(ALERT_TYPE_CHOICES)[self.alert_type]

    @property
    def status_label(self):
        return dict(STATUS_CHOICES)[self.status]


def _minutes_between(now, timestamp):
    if not timestamp:
        return None
    return max(0, int((now - timestamp).total_seconds() // 60))


def _alert_matches(alert, filters):
    search_query = filters.get("q", "").strip().lower()
    if search_query:
        haystack = " ".join(
            [
                alert.title,
                alert.message,
                alert.route_label,
                alert.bus_code,
                alert.severity_label,
                alert.alert_type_label,
                alert.trip_status,
                alert.status_label,
            ]
        ).lower()
        if search_query not in haystack:
            return False

    if filters.get("severity") and alert.severity != filters["severity"]:
        return False
    if filters.get("status") and alert.status != filters["status"]:
        return False
    if filters.get("type") and alert.alert_type != filters["type"]:
        return False
    if filters.get("route") and str(alert.route_id or "") != filters["route"]:
        return False
    if filters.get("bus") and str(alert.bus_id or "") != filters["bus"]:
        return False
    return True


def _build_alert(*, severity, alert_type, status, title, message, timestamp, assignment):
    return OperationalAlert(
        severity=severity,
        alert_type=alert_type,
        status=status,
        title=title,
        message=message,
        timestamp=timestamp,
        route_id=assignment.trip.schedule_slot.route_id if assignment else None,
        route_label=assignment.trip.route_label if assignment else "System",
        bus_id=assignment.bus_id if assignment else None,
        bus_code=assignment.bus.code if assignment else "Fleet",
        trip_id=assignment.trip_id if assignment else None,
        trip_status=assignment.trip.status_label if assignment else "System",
    )


def _generate_assignment_alerts(assignment, *, now, booking_count, telemetry_items, fuel_items):
    alerts = []
    trip = assignment.trip
    bus = assignment.bus
    latest_telemetry = telemetry_items[0] if telemetry_items else None
    latest_fuel = fuel_items[0] if fuel_items else None
    trip_status = trip.get_effective_status(now)
    telemetry_age = _minutes_between(now, latest_telemetry.reported_at) if latest_telemetry else None
    occupancy_ratio = (booking_count / bus.seat_capacity) if bus.seat_capacity else 0
    delay_minutes = latest_telemetry.delay_minutes if latest_telemetry else 0
    traffic_level = latest_telemetry.traffic_level if latest_telemetry else ""
    recent_completion_cutoff = now - timedelta(hours=RECENT_COMPLETION_WINDOW_HOURS)
    issue_detected = False

    if not bus.is_active and trip_status in {Trip.STATUS_SCHEDULED, Trip.STATUS_BOOKING_OPEN, Trip.STATUS_ACTIVE}:
        issue_detected = True
        alerts.append(
            _build_alert(
                severity="critical" if trip_status == Trip.STATUS_ACTIVE else "warning",
                alert_type="operations",
                status="active",
                title="Bus offline",
                message=f"{bus.code} is marked inactive while assigned to {trip.route_label}. Reassign or restore the vehicle before service impact widens.",
                timestamp=trip.start_at,
                assignment=assignment,
            )
        )

    if latest_fuel and latest_fuel.reported_at >= now - timedelta(days=2):
        variance = latest_fuel.variance_percent
        if variance >= Decimal("20.00"):
            issue_detected = True
            alerts.append(
                _build_alert(
                    severity="critical",
                    alert_type="fuel",
                    status="active",
                    title="Fuel variance detected",
                    message=f"{bus.code} is consuming {variance}% above expected fuel usage on {trip.route_label}.",
                    timestamp=latest_fuel.reported_at,
                    assignment=assignment,
                )
            )
        elif variance >= Decimal("10.00"):
            issue_detected = True
            alerts.append(
                _build_alert(
                    severity="warning",
                    alert_type="fuel",
                    status="active",
                    title="Fuel variance detected",
                    message=f"{bus.code} is {variance}% above expected fuel usage. Monitor the route and inspect for inefficiency.",
                    timestamp=latest_fuel.reported_at,
                    assignment=assignment,
                )
            )

    if trip_status == Trip.STATUS_BOOKING_OPEN:
        if occupancy_ratio >= 0.97:
            issue_detected = True
            alerts.append(
                _build_alert(
                    severity="critical",
                    alert_type="booking",
                    status="active",
                    title="Seat capacity nearly full",
                    message=f"{bus.code} is {booking_count}/{bus.seat_capacity} seats booked for {trip.route_label}. Booking pressure is at the limit.",
                    timestamp=now,
                    assignment=assignment,
                )
            )
        elif occupancy_ratio >= 0.85:
            issue_detected = True
            alerts.append(
                _build_alert(
                    severity="warning",
                    alert_type="booking",
                    status="monitoring",
                    title="Seat capacity nearly full",
                    message=f"{bus.code} has reached {booking_count}/{bus.seat_capacity} confirmed seats on {trip.route_label}.",
                    timestamp=now,
                    assignment=assignment,
                )
            )

    if trip_status == Trip.STATUS_ACTIVE:
        if not latest_telemetry:
            issue_detected = True
            alerts.append(
                _build_alert(
                    severity="critical",
                    alert_type="telemetry",
                    status="active",
                    title="No telemetry available",
                    message=f"{bus.code} is active on {trip.route_label}, but no telemetry snapshots have been recorded yet.",
                    timestamp=trip.start_at,
                    assignment=assignment,
                )
            )
        else:
            if not latest_telemetry.is_online:
                issue_detected = True
                alerts.append(
                    _build_alert(
                        severity="critical",
                        alert_type="telemetry",
                        status="active",
                        title="Telemetry offline",
                        message=f"{bus.code} stopped streaming telemetry while running {trip.route_label}.",
                        timestamp=latest_telemetry.reported_at,
                        assignment=assignment,
                    )
                )
            elif telemetry_age is not None and telemetry_age >= TELEMETRY_GAP_MINUTES:
                issue_detected = True
                alerts.append(
                    _build_alert(
                        severity="critical" if telemetry_age >= 25 else "warning",
                        alert_type="telemetry",
                        status="active",
                        title="No telemetry for active trip",
                        message=f"{bus.code} has not sent telemetry for {telemetry_age} minutes while {trip.route_label} is active.",
                        timestamp=latest_telemetry.reported_at,
                        assignment=assignment,
                    )
                )

            if delay_minutes >= 20 or (traffic_level == TelemetrySnapshot.TRAFFIC_HEAVY and delay_minutes >= 12):
                issue_detected = True
                alerts.append(
                    _build_alert(
                        severity="critical" if delay_minutes >= 30 else "warning",
                        alert_type="traffic",
                        status="active",
                        title="Traffic pressure rising",
                        message=f"{trip.route_label} is delayed by {delay_minutes} minutes with {traffic_level} traffic conditions.",
                        timestamp=latest_telemetry.reported_at,
                        assignment=assignment,
                    )
                )

            if len(telemetry_items) >= 2 and latest_telemetry.is_online:
                previous_telemetry = telemetry_items[1]
                gap_minutes = _minutes_between(latest_telemetry.reported_at, previous_telemetry.reported_at)
                if gap_minutes is not None and gap_minutes >= TELEMETRY_GAP_MINUTES:
                    alerts.append(
                        _build_alert(
                            severity="info",
                            alert_type="telemetry",
                            status="resolved",
                            title="Sensor sync restored",
                            message=f"{bus.code} resumed telemetry after a {gap_minutes}-minute data gap on {trip.route_label}.",
                            timestamp=latest_telemetry.reported_at,
                            assignment=assignment,
                        )
                    )

            if (
                not issue_detected
                and latest_telemetry.is_online
                and telemetry_age is not None
                and telemetry_age < RECENT_TELEMETRY_MINUTES
                and delay_minutes <= 5
                and traffic_level in {TelemetrySnapshot.TRAFFIC_LIGHT, TelemetrySnapshot.TRAFFIC_MODERATE}
            ):
                alerts.append(
                    _build_alert(
                        severity="success",
                        alert_type="operations",
                        status="monitoring",
                        title="Route health stable",
                        message=f"{trip.route_label} is streaming clean telemetry with low delay and steady movement from {bus.code}.",
                        timestamp=latest_telemetry.reported_at,
                        assignment=assignment,
                    )
                )

    if trip_status == Trip.STATUS_COMPLETED and trip.end_at >= recent_completion_cutoff:
        resolved_time = latest_telemetry.reported_at if latest_telemetry else trip.end_at
        if delay_minutes <= 10 and (not latest_fuel or latest_fuel.variance_percent < Decimal("10.00")):
            alerts.append(
                _build_alert(
                    severity="success",
                    alert_type="schedule",
                    status="resolved",
                    title="Trip ended successfully",
                    message=f"{trip.route_label} completed with manageable delay and no major fuel exception for {bus.code}.",
                    timestamp=resolved_time,
                    assignment=assignment,
                )
            )

    return alerts


def generate_operational_alerts(*, now=None):
    now = now or timezone.localtime()
    assignments = list(
        TripBusAssignment.objects.select_related(
            "bus",
            "driver",
            "trip__schedule_slot__route__group__section",
        ).filter(
            Q(trip__service_date__gte=now.date() - timedelta(days=1))
            | Q(trip__status__in=[Trip.STATUS_ACTIVE, Trip.STATUS_BOOKING_OPEN, Trip.STATUS_SCHEDULED, Trip.STATUS_COMPLETED])
        )
    )
    assignment_ids = [assignment.id for assignment in assignments]

    booking_counts = {
        row["assignment_id"]: row["count"]
        for row in Booking.objects.filter(
            assignment_id__in=assignment_ids,
            status=Booking.STATUS_CONFIRMED,
        )
        .values("assignment_id")
        .annotate(count=Count("id"))
    }

    telemetry_lookup = defaultdict(list)
    for telemetry in TelemetrySnapshot.objects.filter(assignment_id__in=assignment_ids).select_related("assignment__bus", "assignment__trip"):
        telemetry_lookup[telemetry.assignment_id].append(telemetry)

    fuel_lookup = defaultdict(list)
    for reading in FuelReading.objects.filter(assignment_id__in=assignment_ids).select_related("assignment__bus", "assignment__trip"):
        fuel_lookup[reading.assignment_id].append(reading)

    alerts = []
    for assignment in assignments:
        alerts.extend(
            _generate_assignment_alerts(
                assignment,
                now=now,
                booking_count=booking_counts.get(assignment.id, 0),
                telemetry_items=telemetry_lookup.get(assignment.id, []),
                fuel_items=fuel_lookup.get(assignment.id, []),
            )
        )

    alerts.sort(key=lambda item: (SEVERITY_RANK[item.severity], -(item.timestamp.timestamp() if item.timestamp else 0)))
    return alerts


def filter_operational_alerts(*, alerts, filters):
    return [alert for alert in alerts if _alert_matches(alert, filters)]


def build_alert_summary(alerts):
    return {
        "total": len(alerts),
        "critical": sum(1 for alert in alerts if alert.severity == "critical"),
        "warning": sum(1 for alert in alerts if alert.severity == "warning"),
        "success": sum(1 for alert in alerts if alert.severity == "success"),
        "info": sum(1 for alert in alerts if alert.severity == "info"),
    }


def get_alert_filter_options():
    return {
        "severity_options": SEVERITY_CHOICES,
        "type_options": ALERT_TYPE_CHOICES,
        "status_options": STATUS_CHOICES,
        "route_options": Route.objects.order_by("label").values("id", "label"),
        "bus_options": Bus.objects.order_by("code").values("id", "code"),
    }
