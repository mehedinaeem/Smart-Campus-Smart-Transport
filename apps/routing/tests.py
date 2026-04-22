import datetime

from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from apps.routing.models import Bus, Route, ScheduleSlot, Trip, TripBusAssignment


class TripAssignmentFlowTests(TestCase):
    def setUp(self):
        self.student = User.objects.create_user(username="student_case", password="CampusPass123")
        self.driver = User.objects.create_user(username="driver_case", password="CampusPass123")
        self.driver.profile.role = "driver"
        self.driver.profile.save(update_fields=["role"])
        self.bus = Bus.objects.first()
        self.now = timezone.localtime()
        self.route = Route.objects.first()

    def create_slot(self, time_value):
        return ScheduleSlot.objects.create(route=self.route, departure_time=time_value, display_order=999)

    def build_trip(
        self,
        slot,
        *,
        service_date=None,
        end_offset_minutes=60,
        booking_open_offset_minutes=-30,
        booking_close_offset_minutes=15,
        status=Trip.STATUS_SCHEDULED,
    ):
        service_date = service_date or self.now.date()
        start_dt = timezone.make_aware(datetime.datetime.combine(service_date, slot.departure_time))
        end_dt = start_dt + datetime.timedelta(minutes=end_offset_minutes)
        booking_open_dt = start_dt + datetime.timedelta(minutes=booking_open_offset_minutes)
        booking_close_dt = start_dt + datetime.timedelta(minutes=booking_close_offset_minutes)
        return Trip.objects.create(
            schedule_slot=slot,
            service_date=start_dt.date(),
            start_time=start_dt.time().replace(second=0, microsecond=0),
            end_time=end_dt.time().replace(second=0, microsecond=0),
            booking_open_time=booking_open_dt.time().replace(second=0, microsecond=0),
            booking_close_time=booking_close_dt.time().replace(second=0, microsecond=0),
            status=status,
        )

    def test_overlapping_bus_assignment_is_blocked(self):
        slot_1 = self.create_slot(datetime.time(7, 0))
        slot_2 = self.create_slot(datetime.time(8, 0))

        trip_1 = self.build_trip(slot_1, end_offset_minutes=120, booking_close_offset_minutes=60)
        trip_2 = self.build_trip(slot_2, end_offset_minutes=120, booking_close_offset_minutes=60)

        TripBusAssignment.objects.create(trip=trip_1, bus=self.bus, driver=self.driver)
        overlapping_assignment = TripBusAssignment(trip=trip_2, bus=self.bus)

        with self.assertRaises(ValidationError):
            overlapping_assignment.full_clean()

    def test_seat_booking_shows_only_booking_open_assignments(self):
        self.client.login(username="student_case", password="CampusPass123")
        open_start = (self.now + datetime.timedelta(minutes=10)).time().replace(second=0, microsecond=0)
        closed_start = (self.now + datetime.timedelta(hours=3)).time().replace(second=0, microsecond=0)
        slot_open = self.create_slot(open_start)
        slot_closed = self.create_slot(closed_start)

        open_trip = self.build_trip(slot_open, booking_open_offset_minutes=-10, booking_close_offset_minutes=30)
        closed_trip = self.build_trip(slot_closed, booking_open_offset_minutes=-120, booking_close_offset_minutes=-90)

        TripBusAssignment.objects.create(trip=open_trip, bus=self.bus, driver=self.driver)
        TripBusAssignment.objects.create(trip=closed_trip, bus=Bus.objects.exclude(pk=self.bus.pk).first())

        response = self.client.get(reverse("seat-booking"))

        self.assertContains(response, open_trip.route_label)
        self.assertContains(response, self.bus.code)
        self.assertNotContains(response, Bus.objects.exclude(pk=self.bus.pk).first().code)

    def test_live_tracking_hides_completed_trip_assignments(self):
        active_start = (self.now + datetime.timedelta(minutes=20)).time().replace(second=0, microsecond=0)
        completed_start = (self.now - datetime.timedelta(hours=2)).time().replace(second=0, microsecond=0)
        slot_active = self.create_slot(active_start)
        slot_completed = self.create_slot(completed_start)

        active_trip = self.build_trip(slot_active, booking_open_offset_minutes=-15, booking_close_offset_minutes=20)
        completed_trip = self.build_trip(
            slot_completed,
            service_date=self.now.date() - datetime.timedelta(days=1),
            booking_open_offset_minutes=-30,
            booking_close_offset_minutes=-10,
        )

        active_bus = self.bus
        completed_bus = Bus.objects.exclude(pk=active_bus.pk).first()

        TripBusAssignment.objects.create(trip=active_trip, bus=active_bus, driver=self.driver)
        TripBusAssignment.objects.create(trip=completed_trip, bus=completed_bus)

        response = self.client.get(reverse("live-tracking"))

        self.assertContains(response, active_trip.route_label)
        self.assertContains(response, active_bus.code)
        self.assertNotContains(response, completed_bus.code)
