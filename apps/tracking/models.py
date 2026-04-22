from decimal import Decimal

from django.db import models
from django.utils import timezone

from apps.routing.models import Bus, Trip, TripBusAssignment


class BusDevice(models.Model):
    bus = models.ForeignKey(Bus, on_delete=models.CASCADE, related_name="devices")
    identifier = models.CharField(max_length=80, unique=True)
    api_key = models.CharField(max_length=120)
    label = models.CharField(max_length=120, blank=True)
    firmware_version = models.CharField(max_length=40, blank=True)
    is_active = models.BooleanField(default=True)
    last_seen_at = models.DateTimeField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["bus__code", "identifier"]

    def __str__(self):
        return self.label or self.identifier


class BusLocation(models.Model):
    bus = models.ForeignKey(Bus, on_delete=models.CASCADE, related_name="locations")
    assignment = models.ForeignKey(
        TripBusAssignment,
        on_delete=models.SET_NULL,
        related_name="locations",
        blank=True,
        null=True,
    )
    trip = models.ForeignKey(Trip, on_delete=models.SET_NULL, related_name="locations", blank=True, null=True)
    device = models.ForeignKey(BusDevice, on_delete=models.SET_NULL, related_name="locations", blank=True, null=True)
    latitude = models.DecimalField(max_digits=9, decimal_places=6)
    longitude = models.DecimalField(max_digits=9, decimal_places=6)
    speed_kph = models.DecimalField(max_digits=6, decimal_places=2, default=Decimal("0.00"))
    heading = models.DecimalField(max_digits=6, decimal_places=2, blank=True, null=True)
    ignition_on = models.BooleanField(blank=True, null=True)
    recorded_at = models.DateTimeField(default=timezone.now, db_index=True)
    received_at = models.DateTimeField(auto_now_add=True)
    raw_payload = models.JSONField(default=dict, blank=True)

    class Meta:
        ordering = ["-recorded_at", "-id"]
        indexes = [
            models.Index(fields=["bus", "-recorded_at"]),
            models.Index(fields=["assignment", "-recorded_at"]),
        ]

    def __str__(self):
        return f"{self.bus.code} @ {timezone.localtime(self.recorded_at).strftime('%Y-%m-%d %I:%M:%S %p')}"
