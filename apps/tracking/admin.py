from django.contrib import admin

from .models import BusDevice, BusLocation


@admin.register(BusDevice)
class BusDeviceAdmin(admin.ModelAdmin):
    list_display = ("identifier", "bus", "label", "is_active", "last_seen_at")
    list_filter = ("is_active",)
    search_fields = ("identifier", "bus__code", "label")


@admin.register(BusLocation)
class BusLocationAdmin(admin.ModelAdmin):
    list_display = ("bus", "assignment", "recorded_at", "speed_kph", "ignition_on")
    list_filter = ("bus", "ignition_on")
    search_fields = ("bus__code", "assignment__trip__schedule_slot__route__label")
