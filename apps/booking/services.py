from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.mail import send_mail
from django.db import transaction
from django.utils import timezone

from apps.routing.models import Trip, TripBusAssignment
from apps.routing.services import get_booking_assignments

from .models import Booking


DEFAULT_SEATS_PER_ROW = 6
PREMIUM_SEAT_CODES = {"A1", "A2", "A3", "A4"}


def get_available_assignments(now=None):
    return get_booking_assignments(now=now)


def generate_seat_codes(capacity):
    seat_codes = []
    for index in range(capacity):
        row = chr(ord("A") + (index // DEFAULT_SEATS_PER_ROW))
        col = (index % DEFAULT_SEATS_PER_ROW) + 1
        seat_codes.append(f"{row}{col}")
    return seat_codes


def get_booked_seats(assignment):
    return set(
        Booking.objects.filter(
            assignment=assignment,
            status=Booking.STATUS_CONFIRMED,
        ).values_list("seat_number", flat=True)
    )


def build_seat_layout(assignment, user=None):
    capacity = assignment.bus.seat_capacity
    booked = get_booked_seats(assignment)
    active_booking = get_user_active_booking(user) if user and user.is_authenticated else None
    active_booking_seat = active_booking.seat_number if active_booking and active_booking.assignment_id == assignment.id else None

    seats = []
    for code in generate_seat_codes(capacity):
        if code == active_booking_seat:
            state = "selected"
        elif code in booked:
            state = "booked"
        elif code in PREMIUM_SEAT_CODES:
            state = "premium"
        else:
            state = "available"
        seats.append({"code": code, "state": state})
    return seats


def get_user_active_booking(user):
    if not user or not user.is_authenticated:
        return None

    for booking in Booking.objects.select_related(
        "assignment__trip__schedule_slot__route",
        "assignment__bus",
    ).filter(user=user, status=Booking.STATUS_CONFIRMED):
        if booking.is_active_booking:
            return booking
    return None


def get_user_booking_history(user):
    if not user or not user.is_authenticated:
        return []

    history = [
        booking
        for booking in Booking.objects.select_related(
            "assignment__trip__schedule_slot__route",
            "assignment__bus",
        ).filter(user=user)
        if not booking.is_active_booking
    ]
    history.sort(key=lambda item: (item.assignment.trip.service_date, item.assignment.trip.start_time), reverse=True)
    return history


def get_booking_assignment_for_user(assignment_id, user):
    return next((assignment for assignment in get_available_assignments() if assignment.pk == assignment_id), None)


@transaction.atomic
def create_booking(*, user, assignment, seat_number):
    booking = Booking(
        user=user,
        assignment=assignment,
        seat_number=seat_number.strip().upper(),
    )
    booking.full_clean()
    booking.save()
    send_booking_confirmation_email(booking)
    return booking


def send_booking_confirmation_email(booking):
    user = booking.user
    if not user.email:
        return

    student_name = user.get_full_name() or user.username
    trip = booking.assignment.trip
    subject = "Booking Confirmation - Smart Campus"
    body = (
        f"Hello {student_name},\n\n"
        "Your seat booking has been confirmed.\n\n"
        f"Bus Number: {booking.assignment.bus.code}\n"
        f"Seat Number: {booking.seat_number}\n"
        f"Trip Date: {trip.service_date}\n"
        f"Trip Time: {trip.start_time.strftime('%I:%M %p')}\n"
        f"Route: {trip.route_label}\n"
        f"Booking Token: {booking.token}\n\n"
        "Please keep this information ready before boarding.\n"
        "Thank you for using Smart Campus."
    )
    send_mail(
        subject,
        body,
        getattr(settings, "DEFAULT_FROM_EMAIL", "no-reply@smartcampus.local"),
        [user.email],
        fail_silently=False,
    )


def get_dashboard_booking_context(user):
    active_booking = get_user_active_booking(user)
    booking_history = get_user_booking_history(user)
    return {
        "active_booking": active_booking,
        "booking_history": booking_history,
    }
