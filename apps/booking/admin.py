from django.contrib import admin

from .models import Booking


@admin.register(Booking)
class BookingAdmin(admin.ModelAdmin):
    list_display = ("user", "assignment", "seat_number", "status", "created_at")
    list_filter = ("status", "assignment__trip__service_date")
    search_fields = ("user__username", "user__email", "seat_number", "assignment__bus__code")
