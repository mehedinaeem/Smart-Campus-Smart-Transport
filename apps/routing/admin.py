from django.contrib import admin

from .models import Bus, Route, ScheduleSection, ScheduleSlot, Trip, TripBusAssignment, VehicleGroup


class ScheduleSlotInline(admin.TabularInline):
    model = ScheduleSlot
    extra = 0


@admin.register(Route)
class RouteAdmin(admin.ModelAdmin):
    list_display = ("label", "group", "display_order")
    list_filter = ("group__section", "group")
    inlines = [ScheduleSlotInline]


@admin.register(ScheduleSection)
class ScheduleSectionAdmin(admin.ModelAdmin):
    list_display = ("title", "subtitle", "display_order")


@admin.register(VehicleGroup)
class VehicleGroupAdmin(admin.ModelAdmin):
    list_display = ("name", "section", "display_order")
    list_filter = ("section",)


class TripBusAssignmentInline(admin.TabularInline):
    model = TripBusAssignment
    extra = 0


@admin.register(Trip)
class TripAdmin(admin.ModelAdmin):
    list_display = ("route_label", "service_date", "start_time", "end_time", "status")
    list_filter = ("status", "service_date", "schedule_slot__route__group__section")
    search_fields = ("schedule_slot__route__label", "assignments__bus__code")
    inlines = [TripBusAssignmentInline]


@admin.register(Bus)
class BusAdmin(admin.ModelAdmin):
    list_display = ("code", "label", "seat_capacity", "is_active")
    list_filter = ("is_active",)
    search_fields = ("code", "label")
