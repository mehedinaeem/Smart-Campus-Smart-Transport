from datetime import timedelta

from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from apps.routing.models import Bus, Route, RouteStop, ScheduleSection, ScheduleSlot, Trip, TripBusAssignment, VehicleGroup
from .models import BusDevice, BusLocation


class TrackingIntegrationTests(TestCase):
    def setUp(self):
        section = ScheduleSection.objects.create(title="Morning Service", subtitle="North Zone", display_order=1)
        group = VehicleGroup.objects.create(section=section, name="Campus Bus", display_order=1)
        route = Route.objects.create(group=group, label="Engineering Loop", display_order=1)
        RouteStop.objects.create(route=route, name="Gate A", sequence=1, latitude="23.800100", longitude="90.400100")
        RouteStop.objects.create(route=route, name="Library", sequence=2, latitude="23.805500", longitude="90.405500")
        slot = ScheduleSlot.objects.create(route=route, departure_time=timezone.localtime().time(), display_order=1)
        now = timezone.localtime()
        self.trip = Trip.objects.create(
            schedule_slot=slot,
            service_date=now.date(),
            start_time=(now - timedelta(minutes=5)).time(),
            end_time=(now + timedelta(minutes=55)).time(),
            booking_open_time=(now - timedelta(minutes=30)).time(),
            booking_close_time=(now + timedelta(minutes=10)).time(),
            status=Trip.STATUS_ACTIVE,
        )
        self.bus = Bus.objects.create(code="BUS-101", label="Bus 101", seat_capacity=32, is_active=True)
        self.assignment = TripBusAssignment.objects.create(trip=self.trip, bus=self.bus)
        self.device = BusDevice.objects.create(bus=self.bus, identifier="esp32-bus-101", api_key="secret-key")

    def test_device_ingestion_creates_location_and_links_assignment(self):
        response = self.client.post(
            reverse("telemetry-ingest"),
            data={
                "bus_identifier": "esp32-bus-101",
                "api_key": "secret-key",
                "latitude": 23.802345,
                "longitude": 90.402345,
                "speed": 28.4,
                "heading": 91.2,
                "ignition": True,
                "timestamp": timezone.now().isoformat(),
            },
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 201)
        self.assertEqual(BusLocation.objects.count(), 1)
        location = BusLocation.objects.get()
        self.assertEqual(location.assignment, self.assignment)
        self.assertEqual(location.device, self.device)

    def test_live_feed_only_returns_active_or_upcoming_assignments(self):
        completed_bus = Bus.objects.create(code="BUS-202", label="Bus 202", seat_capacity=32, is_active=True)
        completed_trip = Trip.objects.create(
            schedule_slot=self.trip.schedule_slot,
            service_date=self.trip.service_date,
            start_time=(timezone.localtime() - timedelta(hours=2)).time(),
            end_time=(timezone.localtime() - timedelta(hours=1)).time(),
            booking_open_time=(timezone.localtime() - timedelta(hours=3)).time(),
            booking_close_time=(timezone.localtime() - timedelta(hours=2, minutes=15)).time(),
            status=Trip.STATUS_COMPLETED,
        )
        TripBusAssignment.objects.create(trip=completed_trip, bus=completed_bus)

        response = self.client.get(reverse("live-tracking-feed"))

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(len(payload["vehicles"]), 1)
        self.assertEqual(payload["vehicles"][0]["assignment_id"], self.assignment.id)

    def test_live_feed_includes_bus_with_latest_location_without_assignment(self):
        now = timezone.localtime()
        unassigned_bus = Bus.objects.create(code="BUS-303", label="Bus 303", seat_capacity=40, is_active=True)
        BusLocation.objects.create(
            bus=unassigned_bus,
            latitude="23.750000",
            longitude="90.390000",
            speed_kph="18.50",
            recorded_at=now,
            raw_payload={"bus_identifier": "BUS-303"},
        )

        response = self.client.get(reverse("live-tracking-feed"))

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        vehicle = next(item for item in payload["vehicles"] if item["bus_code"] == "BUS-303")
        self.assertEqual(vehicle["assignment_id"], -unassigned_bus.id)
        self.assertEqual(vehicle["route_label"], "Live Bus Location")
        self.assertEqual(vehicle["latitude"], 23.75)
        self.assertEqual(vehicle["longitude"], 90.39)
