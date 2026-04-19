from django.contrib.auth import REDIRECT_FIELD_NAME
from django.contrib.auth.views import redirect_to_login
from django.contrib.messages import constants as message_constants
from django.contrib import messages
from django.shortcuts import redirect
from django.urls import reverse
from django.utils.http import url_has_allowed_host_and_scheme


def get_user_role(user):
    if not user.is_authenticated:
        return "guest"
    if user.is_superuser or user.is_staff:
        return "admin"

    profile = getattr(user, "profile", None)
    if profile and profile.role:
        return profile.role
    return "student"


def get_post_login_url(user):
    role = get_user_role(user)
    if role == "admin":
        return reverse("admin-dashboard")
    if role == "driver":
        return reverse("driver-dashboard")
    return reverse("student-dashboard")


def get_safe_redirect(request, fallback_url):
    next_url = request.POST.get(REDIRECT_FIELD_NAME) or request.GET.get(REDIRECT_FIELD_NAME)
    if next_url and url_has_allowed_host_and_scheme(next_url, {request.get_host()}, require_https=request.is_secure()):
        return next_url
    return fallback_url


def redirect_authenticated_user(request, level=message_constants.INFO, message_text=None):
    if message_text:
        messages.add_message(request, level, message_text)
    return redirect(get_post_login_url(request.user))


def redirect_unauthenticated_user(request, message_text):
    messages.info(request, message_text)
    return redirect_to_login(request.get_full_path(), reverse("login"))
