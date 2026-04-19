from functools import wraps

from django.contrib import messages
from django.shortcuts import redirect

from .auth_utils import get_post_login_url, get_user_role, redirect_unauthenticated_user


def role_required(*allowed_roles, login_message="Please login to continue.", denied_message="You do not have permission to access this page."):
    def decorator(view_func):
        @wraps(view_func)
        def wrapped(request, *args, **kwargs):
            if not request.user.is_authenticated:
                return redirect_unauthenticated_user(request, login_message)

            role = get_user_role(request.user)
            if role not in allowed_roles:
                messages.error(request, denied_message)
                return redirect(get_post_login_url(request.user))

            return view_func(request, *args, **kwargs)

        return wrapped

    return decorator
