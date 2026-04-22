from django.contrib import admin

from .models import FuelReading, TelemetrySnapshot


@admin.register(FuelReading)
class FuelReadingAdmin(admin.ModelAdmin):
    list_display = ("assignment", "expected_liters", "actual_liters", "reported_at")
    list_filter = ("reported_at", "assignment__trip__service_date")
    search_fields = ("assignment__bus__code", "assignment__trip__schedule_slot__route__label", "note")


@admin.register(TelemetrySnapshot)
class TelemetrySnapshotAdmin(admin.ModelAdmin):
    list_display = ("assignment", "reported_at", "traffic_level", "delay_minutes", "speed_kph", "is_online")
    list_filter = ("traffic_level", "is_online", "reported_at", "assignment__trip__service_date")
    search_fields = ("assignment__bus__code", "assignment__trip__schedule_slot__route__label", "note")
