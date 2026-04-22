from django import forms
from django.core.exceptions import ValidationError
from django.forms import BaseInlineFormSet, inlineformset_factory

from apps.core.models import UserProfile

from .models import Bus, ScheduleSlot, Trip, TripBusAssignment


class TimeInput(forms.TimeInput):
    input_type = "time"


class DateInput(forms.DateInput):
    input_type = "date"


class TripForm(forms.ModelForm):
    class Meta:
        model = Trip
        fields = [
            "schedule_slot",
            "service_date",
            "start_time",
            "end_time",
            "booking_open_time",
            "booking_close_time",
            "status",
            "notes",
        ]
        widgets = {
            "service_date": DateInput(),
            "start_time": TimeInput(),
            "end_time": TimeInput(),
            "booking_open_time": TimeInput(),
            "booking_close_time": TimeInput(),
            "notes": forms.Textarea(attrs={"rows": 3}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["schedule_slot"].queryset = ScheduleSlot.objects.select_related("route__group__section").order_by(
            "route__group__section__display_order",
            "route__group__display_order",
            "route__display_order",
            "display_order",
        )
        self.fields["schedule_slot"].label_from_instance = (
            lambda slot: f"{slot.route.group.section.title} • {slot.route.label} • {slot.departure_time.strftime('%I:%M %p')}"
        )


class TripBusAssignmentForm(forms.ModelForm):
    class Meta:
        model = TripBusAssignment
        fields = ["bus", "driver"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["bus"].queryset = Bus.objects.filter(is_active=True)
        self.fields["driver"].queryset = self.fields["driver"].queryset.filter(profile__role=UserProfile.ROLE_DRIVER).order_by(
            "username"
        )
        self.fields["driver"].required = False


class BaseTripBusAssignmentFormSet(BaseInlineFormSet):
    def clean(self):
        super().clean()
        seen_buses = set()
        seen_drivers = set()

        if any(self.errors):
            return

        active_forms = [
            form
            for form in self.forms
            if form.cleaned_data and not form.cleaned_data.get("DELETE", False) and form.cleaned_data.get("bus")
        ]

        if not active_forms:
            raise ValidationError("Add at least one bus assignment for this trip.")

        for form in active_forms:
            bus = form.cleaned_data["bus"]
            driver = form.cleaned_data.get("driver")
            if bus.pk in seen_buses:
                raise ValidationError("A bus can only be listed once per trip.")
            seen_buses.add(bus.pk)

            if driver:
                if driver.pk in seen_drivers:
                    raise ValidationError("A driver can only be listed once per trip.")
                seen_drivers.add(driver.pk)


TripBusAssignmentFormSet = inlineformset_factory(
    Trip,
    TripBusAssignment,
    form=TripBusAssignmentForm,
    formset=BaseTripBusAssignmentFormSet,
    extra=1,
    can_delete=True,
)
