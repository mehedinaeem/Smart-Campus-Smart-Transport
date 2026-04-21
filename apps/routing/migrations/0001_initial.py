from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion

from apps.routing.schedule_seed import SCHEDULE_SEED_DATA, seed_bus_payload


def load_initial_schedule(apps, schema_editor):
    ScheduleSection = apps.get_model("routing", "ScheduleSection")
    VehicleGroup = apps.get_model("routing", "VehicleGroup")
    Route = apps.get_model("routing", "Route")
    ScheduleSlot = apps.get_model("routing", "ScheduleSlot")
    Bus = apps.get_model("routing", "Bus")

    for section_index, section_data in enumerate(SCHEDULE_SEED_DATA["sections"], start=1):
        section = ScheduleSection.objects.create(
            title=section_data["title"],
            subtitle=section_data["subtitle"],
            display_order=section_index,
        )
        for group_index, group_data in enumerate(section_data["groups"], start=1):
            group = VehicleGroup.objects.create(section=section, name=group_data["vehicle"], display_order=group_index)
            for route_index, route_data in enumerate(group_data["routes"], start=1):
                route = Route.objects.create(group=group, label=route_data["label"], display_order=route_index)
                for slot_index, slot_data in enumerate(route_data["times"], start=1):
                    ScheduleSlot.objects.create(
                        route=route,
                        departure_time=slot_data["time"],
                        note=slot_data["note"],
                        display_order=slot_index,
                    )

    for bus_data in seed_bus_payload():
        Bus.objects.create(**bus_data)


def unload_initial_schedule(apps, schema_editor):
    apps.get_model("routing", "ScheduleSection").objects.all().delete()
    apps.get_model("routing", "Bus").objects.all().delete()


class Migration(migrations.Migration):
    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="Bus",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("code", models.CharField(max_length=30, unique=True)),
                ("label", models.CharField(blank=True, max_length=120)),
                ("seat_capacity", models.PositiveIntegerField(default=32)),
                ("is_active", models.BooleanField(default=True)),
            ],
            options={"ordering": ["code"]},
        ),
        migrations.CreateModel(
            name="Route",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("label", models.CharField(max_length=255)),
                ("display_order", models.PositiveIntegerField(default=0)),
            ],
        ),
        migrations.CreateModel(
            name="ScheduleSection",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("title", models.CharField(max_length=120)),
                ("subtitle", models.CharField(max_length=255)),
                ("display_order", models.PositiveIntegerField(default=0)),
            ],
            options={"ordering": ["display_order", "id"]},
        ),
        migrations.CreateModel(
            name="Trip",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("service_date", models.DateField()),
                ("start_time", models.TimeField()),
                ("end_time", models.TimeField()),
                ("booking_open_time", models.TimeField()),
                ("booking_close_time", models.TimeField()),
                ("status", models.CharField(choices=[("scheduled", "Scheduled"), ("booking_open", "Booking Open"), ("active", "Active"), ("completed", "Completed"), ("cancelled", "Cancelled")], default="scheduled", max_length=20)),
                ("notes", models.TextField(blank=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
            ],
            options={"ordering": ["-service_date", "-start_time", "-id"]},
        ),
        migrations.CreateModel(
            name="VehicleGroup",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("name", models.CharField(max_length=120)),
                ("display_order", models.PositiveIntegerField(default=0)),
                ("section", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="groups", to="routing.schedulesection")),
            ],
            options={"ordering": ["section__display_order", "display_order", "id"]},
        ),
        migrations.AddField(
            model_name="route",
            name="group",
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="routes", to="routing.vehiclegroup"),
        ),
        migrations.CreateModel(
            name="ScheduleSlot",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("departure_time", models.TimeField()),
                ("note", models.CharField(blank=True, max_length=255)),
                ("display_order", models.PositiveIntegerField(default=0)),
                ("route", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="schedule_slots", to="routing.route")),
            ],
            options={"ordering": ["route__display_order", "display_order", "departure_time", "id"]},
        ),
        migrations.AddField(
            model_name="trip",
            name="schedule_slot",
            field=models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="trips", to="routing.scheduleslot"),
        ),
        migrations.CreateModel(
            name="TripBusAssignment",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("bus", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="trip_assignments", to="routing.bus")),
                ("driver", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, related_name="trip_bus_assignments", to=settings.AUTH_USER_MODEL)),
                ("trip", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="assignments", to="routing.trip")),
            ],
            options={"ordering": ["trip__service_date", "trip__start_time", "bus__code"]},
        ),
        migrations.AlterUniqueTogether(name="trip", unique_together={("schedule_slot", "service_date", "start_time")}),
        migrations.AlterUniqueTogether(name="tripbusassignment", unique_together={("trip", "bus")}),
        migrations.RunPython(load_initial_schedule, unload_initial_schedule),
    ]
