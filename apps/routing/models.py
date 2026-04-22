import datetime

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.db.models import Q
from django.utils import timezone


class ScheduleSection(models.Model):
    title = models.CharField(max_length=120)
    subtitle = models.CharField(max_length=255)
    display_order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["display_order", "id"]

    def __str__(self):
        return self.subtitle


class VehicleGroup(models.Model):
    section = models.ForeignKey(ScheduleSection, on_delete=models.CASCADE, related_name="groups")
    name = models.CharField(max_length=120)
    display_order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["section__display_order", "display_order", "id"]

    def __str__(self):
        return self.name


class Route(models.Model):
    group = models.ForeignKey(VehicleGroup, on_delete=models.CASCADE, related_name="routes")
    label = models.CharField(max_length=255)
    display_order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["group__display_order", "display_order", "id"]

    def __str__(self):
        return self.label


class ScheduleSlot(models.Model):
    route = models.ForeignKey(Route, on_delete=models.CASCADE, related_name="schedule_slots")
    departure_time = models.TimeField()
    note = models.CharField(max_length=255, blank=True)
    display_order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["route__display_order", "display_order", "departure_time", "id"]

    def __str__(self):
        return f"{self.route.label} at {self.departure_time.strftime('%I:%M %p')}"

    @property
    def display_text(self):
        time_text = self.departure_time.strftime("%I:%M %p")
        return f"{time_text} ({self.note})" if self.note else time_text


class Bus(models.Model):
    code = models.CharField(max_length=30, unique=True)
    label = models.CharField(max_length=120, blank=True)
    seat_capacity = models.PositiveIntegerField(default=32)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["code"]

    def __str__(self):
        return self.label or self.code


class Trip(models.Model):
    STATUS_SCHEDULED = "scheduled"
    STATUS_BOOKING_OPEN = "booking_open"
    STATUS_ACTIVE = "active"
    STATUS_COMPLETED = "completed"
    STATUS_CANCELLED = "cancelled"
    STATUS_CHOICES = [
        (STATUS_SCHEDULED, "Scheduled"),
        (STATUS_BOOKING_OPEN, "Booking Open"),
        (STATUS_ACTIVE, "Active"),
        (STATUS_COMPLETED, "Completed"),
        (STATUS_CANCELLED, "Cancelled"),
    ]

    schedule_slot = models.ForeignKey(ScheduleSlot, on_delete=models.PROTECT, related_name="trips")
    service_date = models.DateField()
    start_time = models.TimeField()
    end_time = models.TimeField()
    booking_open_time = models.TimeField()
    booking_close_time = models.TimeField()
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default=STATUS_SCHEDULED)
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-service_date", "-start_time", "-id"]
        unique_together = [("schedule_slot", "service_date", "start_time")]

    def __str__(self):
        return f"{self.route_label} - {self.service_date} {self.start_time.strftime('%I:%M %p')}"

    @property
    def route_label(self):
        return self.schedule_slot.route.label

    @property
    def vehicle_group_name(self):
        return self.schedule_slot.route.group.name

    @property
    def section_subtitle(self):
        return self.schedule_slot.route.group.section.subtitle

    @property
    def start_at(self):
        return timezone.make_aware(datetime.datetime.combine(self.service_date, self.start_time))

    @property
    def end_at(self):
        return timezone.make_aware(datetime.datetime.combine(self.service_date, self.end_time))

    @property
    def booking_open_at(self):
        return timezone.make_aware(datetime.datetime.combine(self.service_date, self.booking_open_time))

    @property
    def booking_close_at(self):
        return timezone.make_aware(datetime.datetime.combine(self.service_date, self.booking_close_time))

    def get_effective_status(self, moment=None):
        moment = moment or timezone.localtime()
        if self.status == self.STATUS_CANCELLED:
            return self.STATUS_CANCELLED
        if self.status == self.STATUS_COMPLETED or moment > self.end_at:
            return self.STATUS_COMPLETED
        if self.start_at <= moment <= self.end_at:
            return self.STATUS_ACTIVE
        if self.booking_open_at <= moment <= self.booking_close_at:
            return self.STATUS_BOOKING_OPEN
        return self.STATUS_SCHEDULED

    @property
    def effective_status(self):
        return self.get_effective_status()

    @property
    def status_label(self):
        return dict(self.STATUS_CHOICES)[self.effective_status]

    def clean(self):
        errors = {}
        if self.end_time <= self.start_time:
            errors["end_time"] = "End time must be later than start time."
        if self.booking_close_time <= self.booking_open_time:
            errors["booking_close_time"] = "Booking close time must be later than booking open time."
        if self.booking_open_time > self.start_time:
            errors["booking_open_time"] = "Booking should open before or at the trip start time."
        if self.booking_close_time > self.end_time:
            errors["booking_close_time"] = "Booking should close before or at the trip end time."
        if self.schedule_slot_id and self.start_time != self.schedule_slot.departure_time:
            errors["start_time"] = "Start time must match the selected schedule slot departure time."
        if errors:
            raise ValidationError(errors)


class TripBusAssignment(models.Model):
    trip = models.ForeignKey(Trip, on_delete=models.CASCADE, related_name="assignments")
    bus = models.ForeignKey(Bus, on_delete=models.PROTECT, related_name="trip_assignments")
    driver = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="trip_bus_assignments",
        blank=True,
        null=True,
    )

    class Meta:
        ordering = ["trip__service_date", "trip__start_time", "bus__code"]
        unique_together = [("trip", "bus")]

    def __str__(self):
        return f"{self.bus} for {self.trip}"

    def clean(self):
        errors = {}
        if self.driver_id:
            profile = getattr(self.driver, "profile", None)
            if not profile or profile.role != "driver":
                errors["driver"] = "Assigned user must have a driver role."

        if self.trip_id and self.bus_id:
            overlap_filter = Q(trip__service_date=self.trip.service_date) & Q(
                trip__start_time__lt=self.trip.end_time,
                trip__end_time__gt=self.trip.start_time,
            ) & ~Q(trip__status=Trip.STATUS_CANCELLED)

            if TripBusAssignment.objects.filter(overlap_filter, bus=self.bus).exclude(pk=self.pk).exists():
                errors["bus"] = "This bus is already assigned to an overlapping trip."

            if self.driver_id and TripBusAssignment.objects.filter(overlap_filter, driver=self.driver).exclude(pk=self.pk).exists():
                errors["driver"] = "This driver is already assigned to an overlapping trip."

        if errors:
            raise ValidationError(errors)
