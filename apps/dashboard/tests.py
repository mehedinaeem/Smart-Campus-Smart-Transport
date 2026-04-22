import datetime
from decimal import Decimal

from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from apps.booking.models import Booking
from apps.fuel.models import FuelReading, TelemetrySnapshot
from apps.routing.models import Bus, Route, ScheduleSlot, Trip, TripBusAssignment


class AnalyticsPageTests(TestCase):
    def setUp(self):
        self.admin_user = User.objects.create_user(username="analytics_admin", password="CampusPass123", is_staff=True)
        self.student_user = User.objects.create_user(username="analytics_student", password="CampusPass123")
        self.route = Route.objects.first()
        self.bus = Bus.objects.first()
        self.other_bus = Bus.objects.exclude(pk=self.bus.pk).first()
        self.now = timezone.localtime()

    def create_slot(self, time_value):
        return ScheduleSlot.objects.create(route=self.route, departure_time=time_value, display_order=1000)

    def create_assignment(
        self,
        *,
        bus,
        start_offset_minutes,
        trip_duration_minutes=60,
        booking_open_offset_minutes=-30,
        booking_close_offset_minutes=20,
        service_date=None,
        status=Trip.STATUS_SCHEDULED,
    ):
        service_date = service_date or self.now.date()
        start_dt = self.now + datetime.timedelta(minutes=start_offset_minutes)
        start_time = start_dt.time().replace(second=0, microsecond=0)
        slot = self.create_slot(start_time)
        start_at = timezone.make_aware(datetime.datetime.combine(service_date, slot.departure_time))
        trip = Trip.objects.create(
            schedule_slot=slot,
            service_date=service_date,
            start_time=start_at.time().replace(second=0, microsecond=0),
            end_time=(start_at + datetime.timedelta(minutes=trip_duration_minutes)).time().replace(second=0, microsecond=0),
            booking_open_time=(start_at + datetime.timedelta(minutes=booking_open_offset_minutes)).time().replace(second=0, microsecond=0),
            booking_close_time=(start_at + datetime.timedelta(minutes=booking_close_offset_minutes)).time().replace(second=0, microsecond=0),
            status=status,
        )
        return TripBusAssignment.objects.create(trip=trip, bus=bus)

    def book_seats(self, assignment, seat_codes):
        for seat_code in seat_codes:
            user = User.objects.create_user(username=f"user_{assignment.id}_{seat_code}", password="CampusPass123")
            Booking.objects.create(
                user=user,
                assignment=assignment,
                seat_number=seat_code,
                status=Booking.STATUS_CONFIRMED,
            )

    def test_analytics_page_requires_admin_access(self):
        response = self.client.get(reverse("analytics"))
        self.assertEqual(response.status_code, 302)
        self.assertIn(reverse("login"), response.url)

        self.client.login(username="analytics_student", password="CampusPass123")
        denied = self.client.get(reverse("analytics"), follow=True)
        self.assertContains(denied, "Admin access is required for analytics.")

    def test_analytics_page_uses_real_system_data(self):
        self.client.login(username="analytics_admin", password="CampusPass123")

        first_assignment = self.create_assignment(bus=self.bus, start_offset_minutes=-15, trip_duration_minutes=80)
        second_assignment = self.create_assignment(bus=self.other_bus, start_offset_minutes=45)

        self.book_seats(first_assignment, ["A1", "A2", "A3", "A4", "A5", "A6", "B1", "B2", "B3", "B4", "B5", "B6", "C1", "C2", "C3", "C4"])
        self.book_seats(second_assignment, ["A1", "A2", "A3", "A4", "A5", "A6", "B1", "B2"])

        TelemetrySnapshot.objects.create(
            assignment=first_assignment,
            reported_at=self.now - datetime.timedelta(minutes=35),
            speed_kph=0,
            delay_minutes=0,
            traffic_level=TelemetrySnapshot.TRAFFIC_MODERATE,
            is_online=True,
        )
        TelemetrySnapshot.objects.create(
            assignment=first_assignment,
            reported_at=self.now - datetime.timedelta(minutes=3),
            speed_kph=20,
            delay_minutes=3,
            traffic_level=TelemetrySnapshot.TRAFFIC_LIGHT,
            is_online=True,
        )
        TelemetrySnapshot.objects.create(
            assignment=second_assignment,
            reported_at=self.now - datetime.timedelta(minutes=2),
            speed_kph=11,
            delay_minutes=12,
            traffic_level=TelemetrySnapshot.TRAFFIC_HEAVY,
            is_online=True,
        )

        FuelReading.objects.create(
            assignment=first_assignment,
            expected_liters=Decimal("10.00"),
            actual_liters=Decimal("9.20"),
            reported_at=self.now - datetime.timedelta(minutes=6),
        )
        FuelReading.objects.create(
            assignment=second_assignment,
            expected_liters=Decimal("8.00"),
            actual_liters=Decimal("9.60"),
            reported_at=self.now - datetime.timedelta(minutes=4),
        )

        response = self.client.get(reverse("analytics"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "37.5%")
        self.assertContains(response, "50.0%")
        self.assertContains(response, "32 min")
        self.assertContains(response, first_assignment.trip.route_label)
        self.assertContains(response, first_assignment.bus.code)
        self.assertContains(response, "Fuel Efficiency")
        self.assertContains(response, "Operational Risk")
        self.assertContains(response, "Avg Occupancy")
        self.assertNotContains(response, "Morning peak remains the busiest period")
        self.assertNotContains(response, "Electric fleet zones show the strongest efficiency")
