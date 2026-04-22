from dataclasses import dataclass
from decimal import Decimal, InvalidOperation

from django.conf import settings
from django.db.models import Count
from django.utils import timezone
from django.utils.dateparse import parse_datetime

from apps.booking.models import Booking
from apps.fuel.models import TelemetrySnapshot
from apps.routing.models import Bus, Trip, TripBusAssignment

from .models import BusDevice, BusLocation


ONLINE_WINDOW_SECONDS = getattr(settings, "TRACKING_ONLINE_WINDOW_SECONDS", 75)
OFFLINE_WINDOW_SECONDS = getattr(settings, "TRACKING_OFFLINE_WINDOW_SECONDS", 240)
TELEMETRY_SNAPSHOT_INTERVAL_SECONDS = getattr(settings, "TRACKING_SNAPSHOT_INTERVAL_SECONDS", 60)


class TrackingError(Exception):
    pass


@dataclass
class ResolvedTrackingTarget:
    bus: Bus
    device: BusDevice | None
    assignment: TripBusAssignment | None
    trip: Trip | None


def _normalize_identifier(raw_identifier):
    return (raw_identifier or "").strip()


def _parse_decimal(value, field_name, *, minimum=None, maximum=None, required=True):
    if value in {None, ""}:
        if required:
            raise TrackingError(f"{field_name} is required.")
        return None
    try:
        parsed = Decimal(str(value))
    except (InvalidOperation, TypeError, ValueError):
        raise TrackingError(f"{field_name} must be a valid number.")
    if minimum is not None and parsed < Decimal(str(minimum)):
        raise TrackingError(f"{field_name} must be at least {minimum}.")
    if maximum is not None and parsed > Decimal(str(maximum)):
        raise TrackingError(f"{field_name} must be at most {maximum}.")
    return parsed


def _parse_boolean(value):
    if value in {None, ""}:
        return None
    if isinstance(value, bool):
        return value
    normalized = str(value).strip().lower()
    if normalized in {"1", "true", "yes", "on"}:
        return True
    if normalized in {"0", "false", "no", "off"}:
        return False
    raise TrackingError("ignition must be true/false.")


def _parse_reported_at(raw_timestamp):
    if not raw_timestamp:
        return timezone.now()

    parsed = parse_datetime(str(raw_timestamp).strip())
    if not parsed:
        raise TrackingError("timestamp must be an ISO-8601 datetime.")
    if timezone.is_naive(parsed):
        parsed = timezone.make_aware(parsed, timezone.get_current_timezone())
    return parsed


def _assignment_priority_key(assignment, now):
    status = assignment.trip.get_effective_status(now)
    priority = {
        Trip.STATUS_ACTIVE: 0,
        Trip.STATUS_BOOKING_OPEN: 1,
        Trip.STATUS_SCHEDULED: 2,
    }.get(status, 99)
    return (
        priority,
        abs((assignment.trip.start_at - now).total_seconds()),
        assignment.trip.service_date,
        assignment.trip.start_time,
        assignment.id,
    )


def _resolve_assignment(bus, now):
    candidates = [
        assignment
        for assignment in TripBusAssignment.objects.select_related(
            "trip__schedule_slot__route__group__section",
            "bus",
            "driver",
        ).filter(bus=bus)
        if assignment.trip.get_effective_status(now) in {Trip.STATUS_ACTIVE, Trip.STATUS_BOOKING_OPEN, Trip.STATUS_SCHEDULED}
    ]
    if not candidates:
        return None
    candidates.sort(key=lambda assignment: _assignment_priority_key(assignment, now))
    return candidates[0]


def resolve_tracking_target(*, bus_identifier, api_key=None, now=None):
    now = now or timezone.localtime()
    normalized_identifier = _normalize_identifier(bus_identifier)
    if not normalized_identifier:
        raise TrackingError("bus_identifier is required.")

    device = (
        BusDevice.objects.select_related("bus")
        .filter(identifier=normalized_identifier, is_active=True, bus__is_active=True)
        .first()
    )
    shared_api_key = getattr(settings, "TRACKING_SHARED_API_KEY", "")

    if device:
        if api_key != device.api_key:
            raise TrackingError("Invalid device credentials.")
        bus = device.bus
    else:
        bus = Bus.objects.filter(code=normalized_identifier, is_active=True).first()
        if not bus:
            raise TrackingError("No active bus matches the supplied identifier.")
        if shared_api_key and api_key != shared_api_key:
            raise TrackingError("Invalid shared tracking API key.")

    assignment = _resolve_assignment(bus, now)
    return ResolvedTrackingTarget(bus=bus, device=device, assignment=assignment, trip=assignment.trip if assignment else None)


def ingest_device_telemetry(payload):
    if not isinstance(payload, dict):
        raise TrackingError("Telemetry payload must be a JSON object.")

    recorded_at = _parse_reported_at(payload.get("timestamp"))
    target = resolve_tracking_target(
        bus_identifier=payload.get("bus_identifier"),
        api_key=payload.get("api_key"),
        now=recorded_at,
    )

    latitude = _parse_decimal(payload.get("latitude"), "latitude", minimum=-90, maximum=90)
    longitude = _parse_decimal(payload.get("longitude"), "longitude", minimum=-180, maximum=180)
    speed_kph = _parse_decimal(payload.get("speed", 0), "speed", minimum=0, required=False) or Decimal("0.00")
    heading = _parse_decimal(payload.get("heading"), "heading", minimum=0, maximum=360, required=False)
    ignition_on = _parse_boolean(payload.get("ignition"))

    location = BusLocation.objects.create(
        bus=target.bus,
        assignment=target.assignment,
        trip=target.trip,
        device=target.device,
        latitude=latitude,
        longitude=longitude,
        speed_kph=speed_kph,
        heading=heading,
        ignition_on=ignition_on,
        recorded_at=recorded_at,
        raw_payload=payload,
    )

    if target.device:
        BusDevice.objects.filter(pk=target.device.pk).update(last_seen_at=recorded_at)

    if target.assignment:
        _create_snapshot_if_needed(target.assignment, location)

    return {
        "ok": True,
        "bus": target.bus.code,
        "assignment_id": target.assignment.id if target.assignment else None,
        "trip_id": target.trip.id if target.trip else None,
        "recorded_at": timezone.localtime(location.recorded_at).isoformat(),
    }


def _create_snapshot_if_needed(assignment, location):
    latest_snapshot = assignment.telemetry_snapshots.order_by("-reported_at", "-id").first()
    if latest_snapshot:
        elapsed = abs((location.recorded_at - latest_snapshot.reported_at).total_seconds())
        if elapsed < TELEMETRY_SNAPSHOT_INTERVAL_SECONDS:
            return

    TelemetrySnapshot.objects.create(
        assignment=assignment,
        reported_at=location.recorded_at,
        speed_kph=int(location.speed_kph.quantize(Decimal("1"))),
        delay_minutes=0,
        is_online=True,
        note="GPS telemetry ingestion",
    )


def _build_latest_location_lookup(assignments):
    latest_by_assignment = {}
    assignment_ids = [assignment.id for assignment in assignments]
    if not assignment_ids:
        return latest_by_assignment

    locations = BusLocation.objects.filter(assignment_id__in=assignment_ids).select_related("bus", "trip", "assignment")
    for location in locations.order_by("assignment_id", "-recorded_at", "-id"):
        latest_by_assignment.setdefault(location.assignment_id, location)
    return latest_by_assignment


def _build_booking_count_lookup(assignments):
    assignment_ids = [assignment.id for assignment in assignments]
    if not assignment_ids:
        return {}
    rows = (
        Booking.objects.filter(assignment_id__in=assignment_ids, status=Booking.STATUS_CONFIRMED)
        .values("assignment_id")
        .annotate(total=Count("id"))
    )
    return {row["assignment_id"]: row["total"] for row in rows}


def _serialize_stop(stop):
    eta_minutes = stop.eta_offset_minutes
    eta_label = f"{eta_minutes} min" if eta_minutes is not None else "ETA pending"
    return {
        "id": stop.id,
        "name": stop.name,
        "sequence": stop.sequence,
        "latitude": float(stop.latitude) if stop.latitude is not None else None,
        "longitude": float(stop.longitude) if stop.longitude is not None else None,
        "eta_label": eta_label,
    }


def _get_live_status(trip_status, location_age_seconds, has_location):
    if not has_location:
        return "Unavailable"
    if location_age_seconds is None:
        return "Unavailable"
    if location_age_seconds <= ONLINE_WINDOW_SECONDS:
        return "Active" if trip_status == Trip.STATUS_ACTIVE else "Upcoming"
    if location_age_seconds <= OFFLINE_WINDOW_SECONDS:
        return "Recently seen"
    return "Offline"


def _get_live_status_tone(label):
    if label == "Active":
        return "success"
    if label in {"Upcoming", "Recently seen"}:
        return "info"
    return "warning"


def _serialize_assignment(assignment, latest_location, booking_count, now):
    trip = assignment.trip
    route = trip.schedule_slot.route
    trip_status = trip.get_effective_status(now)
    location_age_seconds = None
    if latest_location:
        location_age_seconds = max(0, int((now - latest_location.recorded_at).total_seconds()))
    live_status = _get_live_status(trip_status, location_age_seconds, bool(latest_location))
    stops = [_serialize_stop(stop) for stop in route.stops.all()]
    route_points = [
        [stop_data["latitude"], stop_data["longitude"]]
        for stop_data in stops
        if stop_data["latitude"] is not None and stop_data["longitude"] is not None
    ]
    driver_name = "Unassigned"
    if assignment.driver:
        driver_name = assignment.driver.get_full_name() or assignment.driver.username

    return {
        "assignment_id": assignment.id,
        "trip_id": trip.id,
        "bus_id": assignment.bus_id,
        "bus_code": assignment.bus.code,
        "bus_label": assignment.bus.label or assignment.bus.code,
        "route_label": trip.route_label,
        "route_section": trip.section_subtitle,
        "trip_status": trip_status,
        "trip_status_label": trip.status_label,
        "live_status": live_status,
        "live_status_tone": _get_live_status_tone(live_status),
        "driver_name": driver_name,
        "start_time": timezone.localtime(trip.start_at).strftime("%I:%M %p"),
        "end_time": timezone.localtime(trip.end_at).strftime("%I:%M %p"),
        "service_date": trip.service_date.isoformat(),
        "booking_count": booking_count,
        "seat_capacity": assignment.bus.seat_capacity,
        "occupancy_label": f"{booking_count}/{assignment.bus.seat_capacity}",
        "speed_kph": float(latest_location.speed_kph) if latest_location else None,
        "heading": float(latest_location.heading) if latest_location and latest_location.heading is not None else None,
        "ignition_on": latest_location.ignition_on if latest_location else None,
        "last_reported_at": timezone.localtime(latest_location.recorded_at).isoformat() if latest_location else None,
        "last_reported_label": timezone.localtime(latest_location.recorded_at).strftime("%I:%M:%S %p") if latest_location else "No telemetry yet",
        "location_age_seconds": location_age_seconds,
        "latitude": float(latest_location.latitude) if latest_location else None,
        "longitude": float(latest_location.longitude) if latest_location else None,
        "eta_label": timezone.localtime(trip.start_at).strftime("%I:%M %p") if trip_status != Trip.STATUS_ACTIVE else "Live ETA soon",
        "stops": stops,
        "route_points": route_points,
    }


def get_tracking_dashboard_payload(*, selected_assignment_id=None, now=None):
    now = now or timezone.localtime()
    assignments = [
        assignment
        for assignment in TripBusAssignment.objects.select_related(
            "bus",
            "driver",
            "trip__schedule_slot__route__group__section",
        ).prefetch_related("trip__schedule_slot__route__stops")
        if assignment.trip.get_effective_status(now) in {Trip.STATUS_ACTIVE, Trip.STATUS_BOOKING_OPEN, Trip.STATUS_SCHEDULED}
    ]
    assignments.sort(key=lambda item: (item.trip.service_date, item.trip.start_time, item.bus.code))

    latest_locations = _build_latest_location_lookup(assignments)
    booking_counts = _build_booking_count_lookup(assignments)
    vehicles = [
        _serialize_assignment(
            assignment,
            latest_locations.get(assignment.id),
            booking_counts.get(assignment.id, 0),
            now,
        )
        for assignment in assignments
    ]

    selected_vehicle = None
    if vehicles:
        if selected_assignment_id:
            selected_vehicle = next((item for item in vehicles if item["assignment_id"] == selected_assignment_id), None)
        selected_vehicle = selected_vehicle or vehicles[0]

    return {
        "generated_at": timezone.localtime(now).isoformat(),
        "vehicles": vehicles,
        "selected_assignment_id": selected_vehicle["assignment_id"] if selected_vehicle else None,
        "selected_vehicle": selected_vehicle,
        "has_assignments": bool(vehicles),
    }
