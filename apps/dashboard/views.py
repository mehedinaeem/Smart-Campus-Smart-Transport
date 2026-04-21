from django.contrib import messages
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.db.models import Q
from django.shortcuts import get_object_or_404, redirect, render

from apps.core.decorators import role_required
from apps.core.models import UserProfile
from apps.routing.forms import TripBusAssignmentFormSet, TripForm
from apps.routing.models import Trip
from apps.routing.services import get_live_assignments, get_trip_history

from .forms import RoleAssignmentForm


def _coerce_trip_id(raw_value):
    if raw_value in {None, "", "None", "null"}:
        return None
    try:
        return int(raw_value)
    except (TypeError, ValueError):
        return None


@role_required(
    "admin",
    login_message="Please login to access the admin dashboard.",
    denied_message="Admin access is required for this page.",
)
def admin_dashboard_view(request):
    live_assignments = get_live_assignments()
    active_assignments = [assignment for assignment in live_assignments if assignment.trip.effective_status == Trip.STATUS_ACTIVE]
    trips_today = {assignment.trip_id for assignment in live_assignments}
    context = {
        "page_title": "Admin Dashboard",
        "page_name": "admin",
        "summary_cards": [
            {"label": "Active Buses", "value": str(len(active_assignments)), "delta": "Currently moving on assigned trips"},
            {"label": "Upcoming / Live Trips", "value": str(len(trips_today)), "delta": "Based on trip assignments"},
            {"label": "Assigned Buses", "value": str(len(live_assignments)), "delta": "Visible in tracking or booking flows"},
            {"label": "Trip Workspace", "value": "Ready", "delta": "Create and manage assignments"},
        ],
        "trips": live_assignments,
    }
    return render(request, "dashboard/admin_dashboard.html", context)


@role_required(
    "admin",
    login_message="Please login to manage trip assignments.",
    denied_message="Admin access is required for trip assignment management.",
)
def trip_assignments_view(request):
    selected_trip = None
    edit_id = _coerce_trip_id(request.GET.get("edit") or request.POST.get("trip_id"))
    if edit_id:
        selected_trip = get_object_or_404(Trip.objects.prefetch_related("assignments"), pk=edit_id)

    if request.method == "POST" and request.POST.get("action") in {"cancel", "complete"}:
        trip_id = _coerce_trip_id(request.POST.get("trip_id"))
        trip = get_object_or_404(Trip, pk=trip_id)
        trip.status = Trip.STATUS_CANCELLED if request.POST["action"] == "cancel" else Trip.STATUS_COMPLETED
        trip.save(update_fields=["status", "updated_at"])
        messages.success(request, f"Trip for {trip.route_label} was updated to {trip.get_status_display().lower()}.")
        return redirect("trip-assignments")

    if request.method == "POST" and request.POST.get("action") == "save_trip":
        selected_trip = selected_trip or Trip()
        trip_form = TripForm(request.POST, instance=selected_trip)
        assignment_formset = TripBusAssignmentFormSet(request.POST, instance=selected_trip, prefix="assignments")
        if trip_form.is_valid() and assignment_formset.is_valid():
            try:
                trip = trip_form.save(commit=False)
                trip.full_clean()
                trip.save()

                assignment_formset.instance = trip
                assignment_instances = []
                assignment_validation_failed = False
                assignments_to_delete = []
                for form in assignment_formset.forms:
                    if not form.cleaned_data:
                        continue

                    if form.cleaned_data.get("DELETE", False):
                        if form.instance.pk:
                            assignments_to_delete.append(form.instance)
                        continue

                    if not form.cleaned_data.get("bus"):
                        continue
                    assignment = form.save(commit=False)
                    assignment.trip = trip
                    try:
                        assignment.full_clean()
                    except ValidationError as exc:
                        for field, errors in exc.message_dict.items():
                            target_field = field if field in form.fields else None
                            for error in errors:
                                form.add_error(target_field, error)
                        assignment_validation_failed = True
                        continue
                    assignment_instances.append(assignment)

                if assignment_validation_failed:
                    trip_form.add_error(None, "Please resolve the highlighted assignment conflicts.")
                    raise ValidationError({})

                for deleted_instance in assignments_to_delete:
                    deleted_instance.delete()

                for assignment in assignment_instances:
                    assignment.save()

                messages.success(request, "Trip assignment saved successfully.")
                return redirect("trip-assignments")
            except ValidationError as exc:
                if exc.message_dict:
                    for field, errors in exc.message_dict.items():
                        target_field = field if field in trip_form.fields else None
                        for error in errors:
                            trip_form.add_error(target_field, error)
    else:
        trip_form = TripForm(instance=selected_trip)
        assignment_formset = TripBusAssignmentFormSet(instance=selected_trip, prefix="assignments")

    active_trips, history_trips = get_trip_history()
    context = {
        "page_title": "Trip Assignments",
        "page_name": "trip-assignments",
        "trip_form": trip_form,
        "assignment_formset": assignment_formset,
        "selected_trip": selected_trip,
        "active_trips": active_trips,
        "history_trips": history_trips,
    }
    return render(request, "dashboard/trip_assignments.html", context)


@role_required(
    "admin",
    login_message="Please login to access analytics.",
    denied_message="Admin access is required for analytics.",
)
def analytics_view(request):
    context = {
        "page_title": "Analytics",
        "page_name": "analytics",
        "insight_cards": [
            {"label": "Avg Occupancy", "value": "74%", "detail": "Morning peak remains the busiest period"},
            {"label": "On-Time Rate", "value": "93.4%", "detail": "Up 4.1% over last week"},
            {"label": "Alert Resolution", "value": "18 min", "detail": "Mean response time across active routes"},
        ],
        "insight_rows": [
            {"title": "Route Demand", "detail": "North Loop and Dorm Express are driving most seat bookings this week."},
            {"title": "Fuel Efficiency", "detail": "Electric fleet zones show the strongest efficiency during afternoon rotations."},
            {"title": "Operational Risk", "detail": "Two congestion clusters are affecting the Medical Shuttle corridor."},
        ],
    }
    return render(request, "dashboard/analytics.html", context)


@role_required(
    "admin",
    login_message="Please login to manage user roles.",
    denied_message="Admin access is required for role management.",
)
def manage_roles_view(request):
    if request.method == "POST":
        form = RoleAssignmentForm(request.POST)
        if form.is_valid():
            target_user_id = form.cleaned_data["user_id"]
            target_role = form.cleaned_data["role"]

            try:
                target_user = User.objects.select_related("profile").get(pk=target_user_id)
            except User.DoesNotExist:
                messages.error(request, "The selected user could not be found.")
                return redirect("manage-roles")

            if target_user == request.user:
                messages.error(request, "You cannot change your own role from this page.")
                return redirect("manage-roles")

            if target_user.is_superuser or target_user.is_staff:
                messages.error(request, "Admin accounts cannot be changed from role management.")
                return redirect("manage-roles")

            target_user.profile.role = target_role
            target_user.profile.save(update_fields=["role"])
            messages.success(request, f"{target_user.username} is now assigned as {target_role}.")
            return redirect("manage-roles")

        messages.error(request, "Please submit a valid role update.")
        return redirect("manage-roles")

    search_query = request.GET.get("q", "").strip()
    users = User.objects.select_related("profile").order_by("username")
    if search_query:
        users = users.filter(
            Q(username__icontains=search_query)
            | Q(first_name__icontains=search_query)
            | Q(last_name__icontains=search_query)
            | Q(email__icontains=search_query)
        )

    managed_users = []
    for user in users:
        current_role = "admin" if user.is_superuser or user.is_staff else user.profile.role
        if user == request.user:
            can_edit = False
            lock_reason = "Your own account is locked here."
        elif user.is_superuser or user.is_staff:
            can_edit = False
            lock_reason = "Admin account"
        else:
            can_edit = True
            lock_reason = ""

        managed_users.append(
            {
                "id": user.id,
                "username": user.username,
                "full_name": user.get_full_name(),
                "email": user.email,
                "current_role": current_role,
                "can_edit": can_edit,
                "lock_reason": lock_reason,
            }
        )

    context = {
        "page_title": "Manage Roles",
        "page_name": "manage-roles",
        "search_query": search_query,
        "editable_roles": [
            (UserProfile.ROLE_STUDENT, "Student"),
            (UserProfile.ROLE_DRIVER, "Driver"),
        ],
        "managed_users": managed_users,
        "user_summary": {
            "total": User.objects.count(),
            "drivers": UserProfile.objects.filter(role=UserProfile.ROLE_DRIVER, user__is_staff=False, user__is_superuser=False).count(),
            "students": UserProfile.objects.filter(role=UserProfile.ROLE_STUDENT, user__is_staff=False, user__is_superuser=False).count(),
        },
    }
    return render(request, "dashboard/manage_roles.html", context)
