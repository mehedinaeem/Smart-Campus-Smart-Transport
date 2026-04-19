from django.contrib import messages
from django.contrib.auth import login
from django.contrib.auth.views import LoginView, LogoutView
from django.shortcuts import redirect, render
from django.views.generic import FormView

from .auth_utils import get_post_login_url, get_safe_redirect
from .decorators import role_required
from .forms import LoginForm, StudentSignupForm


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
    context = {
        "page_title": "Home",
        "page_name": "dashboard",
        "live_status": {
            "bus": "Campus Loop A2",
            "location": "Near Engineering Gate",
            "eta": "4 min",
            "traffic": "Normal",
            "next_arrival": "08:12 AM",
            "occupancy": "18 / 32 seats",
        },
        "stops": [
            {"name": "Innovation Hub", "eta": "2 min"},
            {"name": "Central Library", "eta": "4 min"},
            {"name": "Dormitory West", "eta": "8 min"},
            {"name": "Medical Center", "eta": "12 min"},
        ],
    }
    return render(request, "core/student_dashboard.html", context)


@role_required(
    "student",
    login_message="Please login to view your booking.",
    denied_message="Only students can access booking details.",
)
def my_booking_view(request):
    context = {
        "page_title": "My Booking",
        "page_name": "my-booking",
        "booking": {
            "route": "Green Line Express",
            "seat": "B3",
            "departure": "08:05 AM",
            "status": "Confirmed",
            "token": "7X9-Q2A",
            "boarding_point": "Central Library",
        },
    }
    return render(request, "core/my_booking.html", context)


@role_required(
    "driver",
    login_message="Please login to access your driver workspace.",
    denied_message="Only drivers can access assigned route data.",
)
def driver_dashboard_view(request):
    context = {
        "page_title": "My Assigned Route",
        "page_name": "driver-dashboard",
        "assignment": {
            "route": "Campus Link South",
            "bus_id": "BUS-17",
            "shift": "07:30 AM - 02:00 PM",
            "supervisor": "Transit Control",
            "next_stop": "Business School",
        },
        "checkpoints": [
            {"label": "Fuel Level", "value": "68%", "detail": "Healthy range"},
            {"label": "Trip Status", "value": "On Schedule", "detail": "No active delay"},
            {"label": "Assigned Zone", "value": "South Corridor", "detail": "5 active stops"},
        ],
    }
    return render(request, "core/driver_dashboard.html", context)
