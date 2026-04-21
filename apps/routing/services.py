from django.utils import timezone

from .models import ScheduleSection, Trip, TripBusAssignment
from .schedule_seed import SCHEDULE_SEED_DATA


def get_schedule_page_content():
    sections = ScheduleSection.objects.prefetch_related("groups__routes__schedule_slots").all()
    schedule_sections = []
    for section in sections:
        groups_payload = []
        for group in section.groups.all():
            routes_payload = []
            for route in group.routes.all():
                routes_payload.append(
                    {
                        "label": route.label,
                        "times": [slot.display_text for slot in route.schedule_slots.all()],
                    }
                )
            groups_payload.append({"vehicle": group.name, "routes": routes_payload})
        schedule_sections.append({"title": section.title, "subtitle": section.subtitle, "groups": groups_payload})

    return {
        "hero_schedule": SCHEDULE_SEED_DATA["hero_schedule"],
        "schedule_cards": SCHEDULE_SEED_DATA["schedule_cards"],
        "schedule_sections": schedule_sections,
    }


def get_trip_assignments_queryset():
    return TripBusAssignment.objects.select_related(
        "bus",
        "driver",
        "trip__schedule_slot__route__group__section",
    )


def get_live_assignments(now=None):
    now = now or timezone.localtime()
    items = [
        assignment
        for assignment in get_trip_assignments_queryset()
        if assignment.trip.get_effective_status(now) in {Trip.STATUS_ACTIVE, Trip.STATUS_SCHEDULED, Trip.STATUS_BOOKING_OPEN}
    ]
    items.sort(key=lambda item: (item.trip.service_date, item.trip.start_time, item.bus.code))
    return items


def get_booking_assignments(now=None):
    now = now or timezone.localtime()
    items = [
        assignment
        for assignment in get_trip_assignments_queryset()
        if assignment.trip.get_effective_status(now) == Trip.STATUS_BOOKING_OPEN
    ]
    items.sort(key=lambda item: (item.trip.service_date, item.trip.start_time, item.bus.code))
    return items


def get_current_driver_assignment(user, now=None):
    now = now or timezone.localtime()
    for assignment in get_trip_assignments_queryset().filter(driver=user):
        if assignment.trip.get_effective_status(now) in {Trip.STATUS_ACTIVE, Trip.STATUS_BOOKING_OPEN, Trip.STATUS_SCHEDULED}:
            return assignment
    return None


def get_trip_history(now=None):
    now = now or timezone.localtime()
    trips = list(
        Trip.objects.select_related("schedule_slot__route__group__section").prefetch_related("assignments__bus", "assignments__driver")
    )
    for trip in trips:
        trip.runtime_status = trip.get_effective_status(now)
    active_or_upcoming = [
        trip for trip in trips if trip.runtime_status in {Trip.STATUS_ACTIVE, Trip.STATUS_BOOKING_OPEN, Trip.STATUS_SCHEDULED}
    ]
    history = [trip for trip in trips if trip.runtime_status in {Trip.STATUS_COMPLETED, Trip.STATUS_CANCELLED}]
    active_or_upcoming.sort(key=lambda item: (item.service_date, item.start_time))
    history.sort(key=lambda item: (item.service_date, item.start_time), reverse=True)
    return active_or_upcoming, history
