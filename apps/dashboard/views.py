from django.contrib import messages
from django.contrib.auth.models import User
from django.db.models import Q
from django.shortcuts import redirect, render

from apps.core.decorators import role_required
from apps.core.models import UserProfile

from .forms import RoleAssignmentForm


@role_required(
    "admin",
    login_message="Please login to access the admin dashboard.",
    denied_message="Admin access is required for this page.",
)
def admin_dashboard_view(request):
    context = {
        "page_title": "Admin Dashboard",
        "page_name": "admin",
        "summary_cards": [
            {"label": "Active Buses", "value": "24", "delta": "+3 online"},
            {"label": "Trips Today", "value": "118", "delta": "+12% vs yesterday"},
            {"label": "Total Bookings", "value": "2,431", "delta": "92% seat utilization"},
            {"label": "Alerts", "value": "07", "delta": "2 require action"},
        ],
        "trips": [
            {"route": "North Loop", "bus": "BUS-04", "status": "Running", "load": "71%", "eta": "3 min"},
            {"route": "Medical Shuttle", "bus": "BUS-11", "status": "Delayed", "load": "52%", "eta": "11 min"},
            {"route": "Dorm Express", "bus": "BUS-08", "status": "Running", "load": "88%", "eta": "6 min"},
            {"route": "Library Connector", "bus": "BUS-17", "status": "Charging", "load": "0%", "eta": "24 min"},
        ],
    }
    return render(request, "dashboard/admin_dashboard.html", context)


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
