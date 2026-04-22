from decimal import Decimal

from django.core.validators import MinValueValidator
from django.db import models
from django.utils import timezone

from apps.routing.models import TripBusAssignment


class FuelReading(models.Model):
    assignment = models.ForeignKey(TripBusAssignment, on_delete=models.CASCADE, related_name="fuel_readings")
    expected_liters = models.DecimalField(max_digits=7, decimal_places=2, validators=[MinValueValidator(Decimal("0.01"))])
    actual_liters = models.DecimalField(max_digits=7, decimal_places=2, validators=[MinValueValidator(Decimal("0.00"))])
    reported_at = models.DateTimeField(default=timezone.now, db_index=True)
    note = models.CharField(max_length=255, blank=True)

    class Meta:
        ordering = ["-reported_at", "-id"]

    def __str__(self):
        return f"{self.assignment.bus.code} fuel @ {timezone.localtime(self.reported_at).strftime('%Y-%m-%d %I:%M %p')}"

    @property
    def variance_percent(self):
        if not self.expected_liters:
            return Decimal("0.00")
        variance = ((self.actual_liters - self.expected_liters) / self.expected_liters) * Decimal("100")
        return variance.quantize(Decimal("0.01"))


class TelemetrySnapshot(models.Model):
    TRAFFIC_LIGHT = "light"
    TRAFFIC_MODERATE = "moderate"
    TRAFFIC_HEAVY = "heavy"
    TRAFFIC_CHOICES = [
        (TRAFFIC_LIGHT, "Light"),
        (TRAFFIC_MODERATE, "Moderate"),
        (TRAFFIC_HEAVY, "Heavy"),
    ]

    assignment = models.ForeignKey(TripBusAssignment, on_delete=models.CASCADE, related_name="telemetry_snapshots")
    reported_at = models.DateTimeField(default=timezone.now, db_index=True)
    speed_kph = models.PositiveIntegerField(default=0)
    delay_minutes = models.IntegerField(default=0)
    occupancy_count = models.PositiveIntegerField(blank=True, null=True)
    traffic_level = models.CharField(max_length=20, choices=TRAFFIC_CHOICES, default=TRAFFIC_MODERATE)
    packet_loss_percent = models.DecimalField(max_digits=5, decimal_places=2, default=Decimal("0.00"))
    is_online = models.BooleanField(default=True)
    note = models.CharField(max_length=255, blank=True)

    class Meta:
        ordering = ["-reported_at", "-id"]

    def __str__(self):
        return f"{self.assignment.bus.code} telemetry @ {timezone.localtime(self.reported_at).strftime('%Y-%m-%d %I:%M %p')}"
