import secrets

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.utils import timezone

from apps.routing.models import Trip, TripBusAssignment


class Booking(models.Model):
    STATUS_CONFIRMED = "confirmed"
    STATUS_CANCELLED = "cancelled"
    STATUS_CHOICES = [
        (STATUS_CONFIRMED, "Confirmed"),
        (STATUS_CANCELLED, "Cancelled"),
    ]

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="bookings")
    assignment = models.ForeignKey(TripBusAssignment, on_delete=models.PROTECT, related_name="bookings")
    seat_number = models.CharField(max_length=10)
    token = models.CharField(max_length=24, unique=True, editable=False)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default=STATUS_CONFIRMED)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at", "-id"]
        constraints = [
            models.UniqueConstraint(fields=["assignment", "seat_number"], name="unique_booking_seat_per_assignment"),
        ]

    def __str__(self):
        return f"{self.user.username} - {self.assignment.bus.code} - {self.seat_number}"

    def save(self, *args, **kwargs):
        if not self.token:
            self.token = self.generate_token()
        super().save(*args, **kwargs)

    @staticmethod
    def generate_token():
        return secrets.token_hex(4).upper()

    @property
    def trip(self):
        return self.assignment.trip

    @property
    def runtime_status(self):
        if self.status == self.STATUS_CANCELLED:
            return self.STATUS_CANCELLED
        trip_status = self.assignment.trip.get_effective_status(timezone.localtime())
        if trip_status == Trip.STATUS_CANCELLED:
            return self.STATUS_CANCELLED
        if trip_status == Trip.STATUS_COMPLETED:
            return Trip.STATUS_COMPLETED
        return self.STATUS_CONFIRMED

    @property
    def is_active_booking(self):
        return self.runtime_status == self.STATUS_CONFIRMED

    @property
    def route_label(self):
        return self.assignment.trip.route_label

    @property
    def trip_time_label(self):
        return f"{self.assignment.trip.service_date} at {self.assignment.trip.start_time.strftime('%I:%M %p')}"

    def clean(self):
        errors = {}

        if self.assignment_id and self.assignment.trip.get_effective_status(timezone.localtime()) != Trip.STATUS_BOOKING_OPEN:
            errors["assignment"] = "This trip is not currently open for booking."

        if self.user_id:
            active_booking_exists = any(
                booking.pk != self.pk and booking.is_active_booking
                for booking in Booking.objects.select_related("assignment__trip").filter(
                    user_id=self.user_id,
                    status=self.STATUS_CONFIRMED,
                )
            )
            if active_booking_exists:
                errors["user"] = "You already have an active booking."

        if self.assignment_id and self.seat_number:
            seat_taken = Booking.objects.filter(
                assignment_id=self.assignment_id,
                seat_number__iexact=self.seat_number,
                status=self.STATUS_CONFIRMED,
            ).exclude(pk=self.pk).exists()
            if seat_taken:
                errors["seat_number"] = "This seat has already been booked for the selected trip."

        if errors:
            raise ValidationError(errors)
