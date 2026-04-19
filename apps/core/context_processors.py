from .auth_utils import get_user_role


def auth_ui(request):
    role = get_user_role(request.user)
    return {
        "user_role": role,
        "is_student": role == "student",
        "is_driver": role == "driver",
        "is_admin_user": role == "admin",
    }
