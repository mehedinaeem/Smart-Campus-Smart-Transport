import datetime
from decimal import Decimal

from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from apps.booking.models import Booking
from apps.routing.models import Bus, Route, ScheduleSlot, Trip, TripBusAssignment

from .models import FuelReading, TelemetrySnapshot


class AlertsMonitoringTests(TestCase):
    def setUp(self):
        self.admin_user = User.objects.create_user(username="alerts_admin", password="CampusPass123", is_staff=True)
        self.student_user = User.objects.create_user(username="alerts_student", password="CampusPass123")
        self.route = Route.objects.first()
        self.bus = Bus.objects.first()
        self.backup_bus = Bus.objects.exclude(pk=self.bus.pk).first()
        self.now = timezone.localtime()

    def create_slot(self, time_value):
        return ScheduleSlot.objects.create(route=self.route, departure_time=time_value, display_order=999)

    def create_assignment(
        self,
        *,
        bus,
        start_offset_minutes,
        trip_duration_minutes=60,
        booking_open_offset_minutes=-30,
        booking_close_offset_minutes=15,
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

    def test_alerts_page_requires_admin_access(self):
        unauthenticated_response = self.client.get(reverse("alerts-monitoring"))
        self.assertEqual(unauthenticated_response.status_code, 302)
        self.assertIn(reverse("login"), unauthenticated_response.url)

        self.client.login(username="alerts_student", password="CampusPass123")
        student_response = self.client.get(reverse("alerts-monitoring"), follow=True)

        self.assertEqual(student_response.status_code, 200)
        self.assertContains(student_response, "Admin access is required for alerts and monitoring.")
        self.assertContains(student_response, "Home")

    def test_alerts_page_uses_real_project_data(self):
        self.client.login(username="alerts_admin", password="CampusPass123")

        active_assignment = self.create_assignment(bus=self.bus, start_offset_minutes=-10, trip_duration_minutes=80)
        booking_assignment = self.create_assignment(
            bus=self.backup_bus,
            start_offset_minutes=25,
            booking_open_offset_minutes=-30,
            booking_close_offset_minutes=20,
        )

        FuelReading.objects.create(
            assignment=active_assignment,
            expected_liters=Decimal("10.00"),
            actual_liters=Decimal("12.80"),
            reported_at=self.now - datetime.timedelta(minutes=8),
        )
        TelemetrySnapshot.objects.create(
            assignment=active_assignment,
            reported_at=self.now - datetime.timedelta(minutes=30),
            speed_kph=0,
            delay_minutes=0,
            traffic_level=TelemetrySnapshot.TRAFFIC_MODERATE,
            is_online=True,
        )
        TelemetrySnapshot.objects.create(
            assignment=active_assignment,
            reported_at=self.now - datetime.timedelta(minutes=2),
            speed_kph=18,
            delay_minutes=18,
            traffic_level=TelemetrySnapshot.TRAFFIC_HEAVY,
            is_online=True,
        )

        for seat_number in ["A1", "A2", "A3", "A4", "A5", "A6", "B1", "B2", "B3", "B4", "B5", "B6", "C1", "C2", "C3", "C4", "C5", "C6", "D1", "D2", "D3", "D4", "D5", "D6", "E1", "E2", "E3", "E4"]:
            Booking.objects.create(
                user=self.student_user,
                assignment=booking_assignment,
                seat_number=seat_number,
                status=Booking.STATUS_CONFIRMED,
            )

        response = self.client.get(reverse("alerts-monitoring"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Fuel variance detected")
        self.assertContains(response, "Traffic pressure rising")
        self.assertContains(response, "Sensor sync restored")
        self.assertContains(response, "Seat capacity nearly full")
        self.assertContains(response, active_assignment.bus.code)
        self.assertContains(response, booking_assignment.bus.code)
        self.assertNotContains(response, "South Gate corridor moved to heavy congestion")

    def test_alert_filters_reduce_results(self):
        self.client.login(username="alerts_admin", password="CampusPass123")
        active_assignment = self.create_assignment(bus=self.bus, start_offset_minutes=-5, trip_duration_minutes=75)

        FuelReading.objects.create(
            assignment=active_assignment,
            expected_liters=Decimal("10.00"),
            actual_liters=Decimal("13.10"),
            reported_at=self.now - datetime.timedelta(minutes=4),
        )
        TelemetrySnapshot.objects.create(
            assignment=active_assignment,
            reported_at=self.now - datetime.timedelta(minutes=1),
            speed_kph=14,
            delay_minutes=22,
            traffic_level=TelemetrySnapshot.TRAFFIC_HEAVY,
            is_online=True,
        )

        response = self.client.get(
            reverse("alerts-monitoring"),
            {
                "severity": "critical",
                "type": "fuel",
                "bus": str(active_assignment.bus_id),
            },
        )

        self.assertContains(response, "Fuel variance detected")
        self.assertNotContains(response, "Traffic pressure rising")
        self.assertContains(response, active_assignment.bus.code)
