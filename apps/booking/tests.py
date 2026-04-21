import datetime

from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.core import mail
from django.test import TestCase, override_settings
from django.urls import reverse
from django.utils import timezone

from apps.booking.models import Booking
from apps.booking.services import create_booking
from apps.routing.models import Bus, Route, ScheduleSlot, Trip, TripBusAssignment


@override_settings(EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend")
class BookingFlowTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="student_booking_case",
            email="student@example.com",
            password="CampusPass123",
            first_name="Student",
            last_name="Case",
        )
        self.route = Route.objects.first()
        self.bus = Bus.objects.first()
        self.now = timezone.localtime()

    def create_slot(self, time_value):
        return ScheduleSlot.objects.create(route=self.route, departure_time=time_value, display_order=999)

    def create_assignment(self, *, start_offset_minutes=15, trip_duration_minutes=45, booking_open_offset_minutes=-20, booking_close_offset_minutes=10, service_date=None):
        service_date = service_date or self.now.date()
        start_time = (self.now + datetime.timedelta(minutes=start_offset_minutes)).time().replace(second=0, microsecond=0)
        slot = self.create_slot(start_time)
        start_dt = timezone.make_aware(datetime.datetime.combine(service_date, slot.departure_time))
        trip = Trip.objects.create(
            schedule_slot=slot,
            service_date=service_date,
            start_time=start_dt.time().replace(second=0, microsecond=0),
            end_time=(start_dt + datetime.timedelta(minutes=trip_duration_minutes)).time().replace(second=0, microsecond=0),
            booking_open_time=(start_dt + datetime.timedelta(minutes=booking_open_offset_minutes)).time().replace(second=0, microsecond=0),
            booking_close_time=(start_dt + datetime.timedelta(minutes=booking_close_offset_minutes)).time().replace(second=0, microsecond=0),
        )
        return TripBusAssignment.objects.create(trip=trip, bus=self.bus)

    def test_successful_booking_sends_confirmation_email(self):
        self.client.login(username="student_booking_case", password="CampusPass123")
        assignment = self.create_assignment()

        response = self.client.post(
            reverse("seat-booking"),
            {"assignment_id": assignment.pk, "seat_number": "A1"},
            follow=True,
        )

        self.assertEqual(response.status_code, 200)
        booking = Booking.objects.get(user=self.user)
        self.assertEqual(booking.seat_number, "A1")
        self.assertEqual(len(mail.outbox), 1)
        self.assertIn("Booking Confirmation - Smart Campus", mail.outbox[0].subject)
        self.assertIn(assignment.bus.code, mail.outbox[0].body)
        self.assertIn("A1", mail.outbox[0].body)
        self.assertIn(assignment.trip.route_label, mail.outbox[0].body)

    def test_user_can_have_only_one_active_booking(self):
        assignment_1 = self.create_assignment(start_offset_minutes=20)
        assignment_2 = self.create_assignment(start_offset_minutes=90)
        create_booking(user=self.user, assignment=assignment_1, seat_number="A1")

        with self.assertRaises(ValidationError):
            create_booking(user=self.user, assignment=assignment_2, seat_number="A2")

    def test_seat_cannot_be_booked_twice_for_same_assignment(self):
        other_user = User.objects.create_user(username="student_booking_other", email="other@example.com", password="CampusPass123")
        assignment = self.create_assignment()
        create_booking(user=self.user, assignment=assignment, seat_number="B2")

        with self.assertRaises(ValidationError):
            create_booking(user=other_user, assignment=assignment, seat_number="B2")

    def test_active_booking_and_history_are_split_by_trip_completion(self):
        self.client.login(username="student_booking_case", password="CampusPass123")
        active_assignment = self.create_assignment(start_offset_minutes=20)
        history_assignment = self.create_assignment(
            start_offset_minutes=-120,
            booking_open_offset_minutes=-150,
            booking_close_offset_minutes=-130,
            service_date=self.now.date() - datetime.timedelta(days=1),
        )
        active_booking = create_booking(user=self.user, assignment=active_assignment, seat_number="C1")
        Booking.objects.create(
            user=self.user,
            assignment=history_assignment,
            seat_number="D1",
            status=Booking.STATUS_CANCELLED,
        )

        dashboard_response = self.client.get(reverse("student-dashboard"))
        my_booking_response = self.client.get(reverse("my-booking"))

        self.assertContains(dashboard_response, active_booking.assignment.bus.code)
        self.assertContains(my_booking_response, active_booking.seat_number)
        self.assertContains(my_booking_response, "D1")
