import math
from collections import defaultdict

from django.db.models import Count, Q
from django.utils import timezone

from apps.booking.models import Booking
from apps.fuel.models import TelemetrySnapshot
from apps.fuel.services import generate_operational_alerts
from apps.routing.models import Trip, TripBusAssignment
from apps.tracking.models import BusLocation


NEAR_STOP_THRESHOLD_KM = 0.35
DEFAULT_MOVING_SPEED_KPH = 18
STOPPED_SPEED_THRESHOLD_KPH = 8
MAX_HOME_STOPS = 5


def _format_time(dt):
    return timezone.localtime(dt).strftime("%I:%M %p")


def _format_coordinates(location):
    if not location:
        return "Location unavailable"
    return f"{float(location.latitude):.5f}, {float(location.longitude):.5f}"


def _format_minutes_label(minutes):
    if minutes is None:
        return "ETA pending"
    if minutes <= 0:
        return "Arriving"
    if minutes == 1:
        return "1 min"
    return f"{minutes} min"


def _haversine_km(lat1, lon1, lat2, lon2):
    radius_km = 6371
    lat1_rad = math.radians(float(lat1))
    lon1_rad = math.radians(float(lon1))
    lat2_rad = math.radians(float(lat2))
    lon2_rad = math.radians(float(lon2))
    delta_lat = lat2_rad - lat1_rad
    delta_lon = lon2_rad - lon1_rad
    a = (
        math.sin(delta_lat / 2) ** 2
        + math.cos(lat1_rad) * math.cos(lat2_rad) * math.sin(delta_lon / 2) ** 2
    )
    return radius_km * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))


def _get_assignment_queryset():
    return (
        TripBusAssignment.objects.select_related(
            "bus",
            "driver",
            "trip__schedule_slot__route__group__section",
        )
        .prefetch_related("trip__schedule_slot__route__stops")
        .annotate(
            confirmed_bookings=Count(
                "bookings",
                filter=Q(bookings__status=Booking.STATUS_CONFIRMED),
                distinct=True,
            )
        )
    )


def _build_latest_location_lookup(assignments):
    latest_by_assignment = {}
    latest_by_bus = {}
    assignment_ids = [assignment.id for assignment in assignments]
    bus_ids = [assignment.bus_id for assignment in assignments]
    if not assignment_ids and not bus_ids:
        return latest_by_assignment, latest_by_bus

    locations = (
        BusLocation.objects.filter(Q(assignment_id__in=assignment_ids) | Q(bus_id__in=bus_ids))
        .select_related("bus", "assignment", "trip")
        .order_by("bus_id", "assignment_id", "-recorded_at", "-id")
    )
    for location in locations:
        latest_by_bus.setdefault(location.bus_id, location)
        if location.assignment_id:
            latest_by_assignment.setdefault(location.assignment_id, location)
    return latest_by_assignment, latest_by_bus


def _build_latest_telemetry_lookup(assignments):
    latest = {}
    assignment_ids = [assignment.id for assignment in assignments]
    if not assignment_ids:
        return latest

    telemetry_items = (
        TelemetrySnapshot.objects.filter(assignment_id__in=assignment_ids)
        .select_related("assignment__trip", "assignment__bus")
        .order_by("assignment_id", "-reported_at", "-id")
    )
    for item in telemetry_items:
        latest.setdefault(item.assignment_id, item)
    return latest


def _get_latest_location_for_assignment(assignment, latest_by_assignment, latest_by_bus):
    return latest_by_assignment.get(assignment.id) or latest_by_bus.get(assignment.bus_id)


def _get_stops_for_assignment(assignment):
    return list(assignment.trip.schedule_slot.route.stops.all())


def _get_nearest_stop(stops, location):
    if not location:
        return None, None

    nearest_stop = None
    nearest_distance = None
    for stop in stops:
        if stop.latitude is None or stop.longitude is None:
            continue
        distance = _haversine_km(location.latitude, location.longitude, stop.latitude, stop.longitude)
        if nearest_distance is None or distance < nearest_distance:
            nearest_stop = stop
            nearest_distance = distance
    return nearest_stop, nearest_distance


def _get_current_location_label(nearest_stop, nearest_distance, location):
    if nearest_stop and nearest_distance is not None:
        if nearest_distance <= NEAR_STOP_THRESHOLD_KM:
            return f"Near {nearest_stop.name}"
        return f"Around {nearest_stop.name}"
    return _format_coordinates(location)


def _get_current_location_detail(nearest_stop, nearest_distance, location):
    if nearest_stop and nearest_distance is not None:
        return f"{nearest_distance:.2f} km from mapped stop"
    if location:
        return "Live GPS coordinates"
    return "No recent GPS data"


def _get_next_stop(stops, current_stop, trip_status):
    if not stops:
        return None
    if trip_status != Trip.STATUS_ACTIVE:
        return stops[0]
    if not current_stop:
        return stops[0]
    for index, stop in enumerate(stops):
        if stop.id != current_stop.id:
            continue
        if index + 1 < len(stops):
            return stops[index + 1]
        return stop
    return stops[0]


def _estimate_eta_minutes(*, location, target_stop, current_stop=None):
    if not target_stop:
        return None
    if (
        location
        and target_stop.latitude is not None
        and target_stop.longitude is not None
    ):
        distance_km = _haversine_km(location.latitude, location.longitude, target_stop.latitude, target_stop.longitude)
        if distance_km <= 0.08:
            return 0
        current_speed = float(location.speed_kph or 0)
        effective_speed = current_speed if current_speed >= STOPPED_SPEED_THRESHOLD_KPH else DEFAULT_MOVING_SPEED_KPH
        return max(1, math.ceil((distance_km / effective_speed) * 60))

    if (
        current_stop
        and current_stop.eta_offset_minutes is not None
        and target_stop.eta_offset_minutes is not None
    ):
        return max(target_stop.eta_offset_minutes - current_stop.eta_offset_minutes, 0)

    if target_stop.eta_offset_minutes is not None:
        return target_stop.eta_offset_minutes

    return None


def _build_upcoming_stops(stops, *, current_stop, next_stop, location, trip_status):
    if not stops:
        return []

    start_index = 0
    if current_stop:
        for index, stop in enumerate(stops):
            if stop.id == current_stop.id:
                start_index = index
                break

    visible_stops = stops[start_index : start_index + MAX_HOME_STOPS]
    items = []
    for stop in visible_stops:
        if current_stop and stop.id == current_stop.id and trip_status == Trip.STATUS_ACTIVE:
            state_label = "Current stop"
            state_tone = "info"
            eta_label = "Now"
        elif next_stop and stop.id == next_stop.id:
            state_label = "Next stop"
            state_tone = "success"
            eta_label = _format_minutes_label(
                _estimate_eta_minutes(
                    location=location,
                    target_stop=stop,
                    current_stop=current_stop,
                )
            )
        else:
            state_label = "Upcoming"
            state_tone = "neutral"
            eta_label = _format_minutes_label(
                _estimate_eta_minutes(
                    location=location,
                    target_stop=stop,
                    current_stop=current_stop,
                )
            )

        items.append(
            {
                "name": stop.name,
                "eta": eta_label,
                "state_label": state_label,
                "state_tone": state_tone,
            }
        )
    return items


def _build_map_stop_labels(stops, current_stop, next_stop):
    labels = []
    for stop in stops[:3]:
        if next_stop and stop.id == next_stop.id:
            prefix = "Next"
        elif current_stop and stop.id == current_stop.id:
            prefix = "Now"
        else:
            prefix = "Stop"
        labels.append(f"{prefix}: {stop.name}")
    return labels


def _get_traffic_status(*, latest_location, latest_telemetry, alerts):
    if latest_telemetry and latest_telemetry.traffic_level:
        traffic_level = latest_telemetry.traffic_level
        label = dict(TelemetrySnapshot.TRAFFIC_CHOICES).get(traffic_level, "Moderate")
        tone = "success" if traffic_level == TelemetrySnapshot.TRAFFIC_LIGHT else "warning" if traffic_level == TelemetrySnapshot.TRAFFIC_MODERATE else "critical"
        return label, tone

    if any(alert.alert_type == "traffic" and alert.severity == "critical" for alert in alerts):
        return "Heavy", "critical"
    if any(alert.alert_type == "traffic" for alert in alerts):
        return "Moderate", "warning"

    if latest_location:
        speed = float(latest_location.speed_kph or 0)
        if speed <= 8:
            return "Heavy", "critical"
        if speed <= 18:
            return "Moderate", "warning"
        return "Normal", "success"

    return "Unknown", "neutral"


def _build_load_summary(assignment):
    capacity = assignment.bus.seat_capacity or 0
    booked = assignment.confirmed_bookings
    seats_left = max(capacity - booked, 0)
    load_factor = (booked / capacity) if capacity else 0
    return {
        "capacity": capacity,
        "booked": booked,
        "seats_left": seats_left,
        "occupancy_label": f"{booked} / {capacity} seats" if capacity else "Capacity unavailable",
        "availability_label": f"{seats_left} seats left" if capacity else "Capacity unavailable",
        "load_factor": load_factor,
    }


def _build_live_fleet_card(active_assignment, latest_location, latest_telemetry, alerts):
    if not active_assignment:
        return {
            "has_active_trip": False,
            "status_label": "No active trips",
            "status_tone": "neutral",
            "title": "Campus movement in real time",
            "subtitle": "Live fleet data will appear here once a trip enters active service.",
            "current_location": "No active trips",
            "current_location_detail": "Waiting for an active assignment",
            "eta_label": "ETA pending",
            "traffic_label": "Unknown",
            "traffic_tone": "traffic-unknown",
            "route_label": None,
            "bus_label": None,
            "map_stops": [],
            "empty_message": "No active trips",
            "latitude": None,
            "longitude": None,
            "route_points": [],
            "stops_payload": [],
        }

    stops = _get_stops_for_assignment(active_assignment)
    current_stop, nearest_distance = _get_nearest_stop(stops, latest_location)
    next_stop = _get_next_stop(stops, current_stop, active_assignment.trip.effective_status)
    eta_minutes = _estimate_eta_minutes(location=latest_location, target_stop=next_stop, current_stop=current_stop)
    stops_payload = [
        {
            "name": stop.name,
            "latitude": float(stop.latitude) if stop.latitude is not None else None,
            "longitude": float(stop.longitude) if stop.longitude is not None else None,
        }
        for stop in stops
    ]
    route_points = [
        [stop_data["latitude"], stop_data["longitude"]]
        for stop_data in stops_payload
        if stop_data["latitude"] is not None and stop_data["longitude"] is not None
    ]
    traffic_label, traffic_tone = _get_traffic_status(
        latest_location=latest_location,
        latest_telemetry=latest_telemetry,
        alerts=alerts,
    )

    return {
        "has_active_trip": True,
        "status_label": "Tracking Active" if latest_location else "Trip Active",
        "status_tone": "success" if latest_location else "warning",
        "title": active_assignment.bus.label or active_assignment.bus.code,
        "subtitle": active_assignment.trip.route_label,
        "current_location": _get_current_location_label(current_stop, nearest_distance, latest_location),
        "current_location_detail": _get_current_location_detail(current_stop, nearest_distance, latest_location),
        "eta_label": _format_minutes_label(eta_minutes),
        "traffic_label": traffic_label,
        "traffic_tone": f"traffic-{traffic_tone}",
        "route_label": active_assignment.trip.route_label,
        "bus_label": active_assignment.bus.code,
        "map_stops": _build_map_stop_labels(stops, current_stop, next_stop),
        "latitude": float(latest_location.latitude) if latest_location else None,
        "longitude": float(latest_location.longitude) if latest_location else None,
        "route_points": route_points,
        "stops_payload": stops_payload,
        "current_stop": current_stop,
        "next_stop": next_stop,
        "upcoming_stops": _build_upcoming_stops(
            stops,
            current_stop=current_stop,
            next_stop=next_stop,
            location=latest_location,
            trip_status=active_assignment.trip.effective_status,
        ),
        "location": latest_location,
    }


def _build_next_arrival_card(next_assignment):
    if not next_assignment:
        return {
            "exists": False,
            "headline": "No scheduled arrivals",
            "detail": "Create or open a trip assignment to show the next incoming bus here.",
            "route_label": None,
            "seat_summary": "Seat availability unavailable",
            "is_booking_open": False,
            "assignment_id": None,
        }

    load_summary = _build_load_summary(next_assignment)
    trip_status = next_assignment.trip.effective_status
    return {
        "exists": True,
        "headline": _format_time(next_assignment.trip.start_at),
        "detail": (
            f"{next_assignment.trip.route_label} on {next_assignment.bus.code} with "
            f"{load_summary['occupancy_label'].lower()}."
        ),
        "route_label": next_assignment.trip.route_label,
        "seat_summary": load_summary["availability_label"],
        "occupancy_label": load_summary["occupancy_label"],
        "trip_status_label": next_assignment.trip.status_label,
        "is_booking_open": trip_status == Trip.STATUS_BOOKING_OPEN,
        "assignment_id": next_assignment.id,
        "bus_code": next_assignment.bus.code,
        "route_name": next_assignment.trip.route_label,
    }


def _assignment_sort_key_for_live_home(assignment, latest_locations, latest_bus_locations, now):
    location = _get_latest_location_for_assignment(assignment, latest_locations, latest_bus_locations)
    location_priority = 0 if location else 1
    if assignment.runtime_status == Trip.STATUS_ACTIVE:
        status_priority = 0
    elif assignment.runtime_status == Trip.STATUS_BOOKING_OPEN:
        status_priority = 1
    else:
        status_priority = 2

    if location:
        freshness = abs((now - location.recorded_at).total_seconds())
    else:
        freshness = float("inf")

    start_delta = abs((assignment.trip.start_at - now).total_seconds())
    return (
        status_priority,
        location_priority,
        freshness,
        start_delta,
        assignment.bus.code,
    )


def _build_info_cards(*, focus_assignment, active_assignments, scheduled_assignments):
    focus_assignment = focus_assignment or (scheduled_assignments[0] if scheduled_assignments else None)
    route_stops = _get_stops_for_assignment(focus_assignment) if focus_assignment else []
    load_summary = _build_load_summary(focus_assignment) if focus_assignment else None

    if load_summary:
        if load_summary["seats_left"] == 0:
            seat_title = "Fully booked"
        elif load_summary["load_factor"] >= 0.75:
            seat_title = f"{load_summary['seats_left']} seats left"
        else:
            seat_title = f"{int((1 - load_summary['load_factor']) * 100)}% availability"
        seat_detail = (
            f"{focus_assignment.trip.route_label} currently has "
            f"{load_summary['occupancy_label'].lower()}."
        )
    else:
        seat_title = "No booking window"
        seat_detail = "Seat confidence will appear once a trip has an assigned bus and booking data."

    if focus_assignment:
        if route_stops:
            route_title = f"{focus_assignment.trip.route_label}"
            route_detail = f"{len(route_stops)} mapped stops on this route."
        else:
            route_title = focus_assignment.trip.route_label
            route_detail = "This route has no mapped stops yet, so stop-by-stop clarity is waiting on RouteStop data."
    else:
        route_title = "Route data idle"
        route_detail = "No current or upcoming trip is available to summarize."

    active_bus_count = len({assignment.bus_id for assignment in active_assignments})
    scheduled_trip_count = len({assignment.trip_id for assignment in scheduled_assignments})
    campus_title = f"{active_bus_count} active buses"
    campus_detail = f"{scheduled_trip_count} live or upcoming trips are currently loaded in the system."

    return [
        {
            "eyebrow": "Seat Confidence",
            "title": seat_title,
            "detail": seat_detail,
        },
        {
            "eyebrow": "Route Clarity",
            "title": route_title,
            "detail": route_detail,
        },
        {
            "eyebrow": "Campus Ready",
            "title": campus_title,
            "detail": campus_detail,
        },
    ]


def get_student_dashboard_snapshot(*, now=None):
    now = now or timezone.localtime()
    assignments = list(_get_assignment_queryset())
    if not assignments:
        return {
            "live_fleet": _build_live_fleet_card(None, None, None, []),
            "next_bus": _build_next_arrival_card(None),
            "stops": [],
            "info_cards": _build_info_cards(
                focus_assignment=None,
                active_assignments=[],
                scheduled_assignments=[],
            ),
        }

    for assignment in assignments:
        assignment.runtime_status = assignment.trip.get_effective_status(now)

    latest_locations, latest_bus_locations = _build_latest_location_lookup(assignments)
    latest_telemetry = _build_latest_telemetry_lookup(assignments)
    alerts = generate_operational_alerts(now=now)
    alerts_by_trip = defaultdict(list)
    for alert in alerts:
        if alert.trip_id:
            alerts_by_trip[alert.trip_id].append(alert)

    active_assignments = [assignment for assignment in assignments if assignment.runtime_status == Trip.STATUS_ACTIVE]
    scheduled_assignments = [
        assignment
        for assignment in assignments
        if assignment.runtime_status in {Trip.STATUS_ACTIVE, Trip.STATUS_BOOKING_OPEN, Trip.STATUS_SCHEDULED}
    ]
    active_assignments.sort(
        key=lambda assignment: _assignment_sort_key_for_live_home(
            assignment,
            latest_locations,
            latest_bus_locations,
            now,
        )
    )
    scheduled_assignments.sort(key=lambda assignment: (assignment.trip.start_at, assignment.bus.code))

    active_assignment = active_assignments[0] if active_assignments else None
    live_home_assignment = active_assignment
    if not live_home_assignment and scheduled_assignments:
        live_home_candidates = [
            assignment
            for assignment in scheduled_assignments
            if _get_latest_location_for_assignment(assignment, latest_locations, latest_bus_locations)
        ]
        if live_home_candidates:
            live_home_candidates.sort(
                key=lambda assignment: _assignment_sort_key_for_live_home(
                    assignment,
                    latest_locations,
                    latest_bus_locations,
                    now,
                )
            )
            live_home_assignment = live_home_candidates[0]

    if live_home_assignment:
        active_location = _get_latest_location_for_assignment(live_home_assignment, latest_locations, latest_bus_locations)
        live_fleet = _build_live_fleet_card(
            live_home_assignment,
            active_location,
            latest_telemetry.get(live_home_assignment.id),
            alerts_by_trip.get(live_home_assignment.trip_id, []),
        )
        stops = live_fleet["upcoming_stops"]
    else:
        live_fleet = _build_live_fleet_card(None, None, None, [])
        stops = []

    next_arrival_candidates = [assignment for assignment in scheduled_assignments if assignment.runtime_status != Trip.STATUS_ACTIVE]
    next_assignment = next_arrival_candidates[0] if next_arrival_candidates else active_assignment

    return {
        "live_fleet": live_fleet,
        "next_bus": _build_next_arrival_card(next_assignment),
        "stops": stops,
        "info_cards": _build_info_cards(
            focus_assignment=active_assignment or next_assignment,
            active_assignments=active_assignments,
            scheduled_assignments=scheduled_assignments,
        ),
    }
