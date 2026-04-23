from django.contrib import messages
from django.contrib.auth import login
from django.contrib.auth.views import LoginView, LogoutView
from django.shortcuts import redirect, render
from django.urls import reverse
from django.views.generic import FormView

from apps.booking.services import get_dashboard_booking_context
from apps.routing.services import get_current_driver_assignment

from .auth_utils import get_post_login_url, get_safe_redirect
from .decorators import role_required
from .forms import LoginForm, StudentSignupForm
from .services import get_student_dashboard_snapshot


class RoleAwareLoginView(LoginView):
    template_name = "auth/login.html"
    authentication_form = LoginForm
    redirect_authenticated_user = True

    def form_valid(self, form):
        messages.success(self.request, "Welcome back. You are now logged in.")
        return super().form_valid(form)

    def get_success_url(self):
        return get_safe_redirect(self.request, get_post_login_url(self.request.user))


class RoleAwareLogoutView(LogoutView):
    def dispatch(self, request, *args, **kwargs):
        if request.user.is_authenticated:
            messages.success(request, "You have been logged out.")
        return super().dispatch(request, *args, **kwargs)


class StudentSignupView(FormView):
    template_name = "auth/signup.html"
    form_class = StudentSignupForm

    def dispatch(self, request, *args, **kwargs):
        if request.user.is_authenticated:
            return redirect(get_post_login_url(request.user))
        return super().dispatch(request, *args, **kwargs)

    def form_valid(self, form):
        user = form.save()
        login(self.request, user)
        messages.success(self.request, "Your student account is ready. Welcome to Smart Campus Transit.")
        return redirect(get_post_login_url(user))


def student_dashboard_view(request):
    dashboard_snapshot = get_student_dashboard_snapshot()
    booking_context = get_dashboard_booking_context(request.user) if request.user.is_authenticated else {
        "active_booking": None,
        "booking_history": [],
    }
    next_bus = dashboard_snapshot["next_bus"]
    if next_bus["assignment_id"]:
        next_bus["booking_url"] = f"{reverse('seat-booking')}?assignment={next_bus['assignment_id']}"
    else:
        next_bus["booking_url"] = reverse("seat-booking")
    next_bus["cta_label"] = "Book Seat" if next_bus["is_booking_open"] else "Booking Closed"
    live_fleet = dashboard_snapshot["live_fleet"]
    home_live_map_payload = {
        "bus_label": live_fleet.get("bus_label"),
        "route_label": live_fleet.get("route_label"),
        "current_location": live_fleet.get("current_location"),
        "latitude": live_fleet.get("latitude"),
        "longitude": live_fleet.get("longitude"),
        "route_points": live_fleet.get("route_points", []),
        "stops_payload": live_fleet.get("stops_payload", []),
    }

    context = {
        "page_title": "Home",
        "page_name": "dashboard",
        "home_live_map_payload": home_live_map_payload,
        **dashboard_snapshot,
        **booking_context,
    }
    return render(request, "core/student_dashboard.html", context)


@role_required(
    "student",
    login_message="Please login to view your booking.",
    denied_message="Only students can access booking details.",
)
def my_booking_view(request):
    booking_context = get_dashboard_booking_context(request.user)
    context = {
        "page_title": "My Booking",
        "page_name": "my-booking",
        **booking_context,
    }
    return render(request, "core/my_booking.html", context)


@role_required(
    "driver",
    login_message="Please login to access your driver workspace.",
    denied_message="Only drivers can access assigned route data.",
)
def driver_dashboard_view(request):
    assignment = get_current_driver_assignment(request.user)
    context = {
        "page_title": "My Assigned Route",
        "page_name": "driver-dashboard",
        "assignment": {
            "route": assignment.trip.route_label if assignment else "No trip assigned yet",
            "bus_id": assignment.bus.code if assignment else "--",
            "shift": (
                f"{assignment.trip.start_time.strftime('%I:%M %p')} - {assignment.trip.end_time.strftime('%I:%M %p')}"
                if assignment
                else "Awaiting assignment"
            ),
            "supervisor": "Transit Control",
            "next_stop": assignment.trip.section_subtitle if assignment else "No active checkpoint",
        },
        "checkpoints": [
            {"label": "Fuel Level", "value": "68%", "detail": "Healthy range"},
            {"label": "Trip Status", "value": assignment.trip.status_label if assignment else "Idle", "detail": "Live from trip assignment"},
            {"label": "Assigned Zone", "value": assignment.trip.section_subtitle if assignment else "No zone", "detail": "Derived from schedule section"},
        ],
        "has_assignment": bool(assignment),
    }
    return render(request, "core/driver_dashboard.html", context)
