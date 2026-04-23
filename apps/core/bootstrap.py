import os
import sys
from threading import Lock, Timer

from django.contrib.auth import get_user_model
from django.db import OperationalError, ProgrammingError, connections

from .models import UserProfile


_bootstrap_lock = Lock()
_bootstrap_attempted = False
_bootstrap_scheduled = False
_skip_commands = {"makemigrations", "migrate", "collectstatic", "shell", "dbshell", "test"}


def _get_superuser_credentials():
    username = os.environ.get("DJANGO_SUPERUSER_USERNAME", "").strip()
    email = os.environ.get("DJANGO_SUPERUSER_EMAIL", "").strip()
    password = os.environ.get("DJANGO_SUPERUSER_PASSWORD", "")
    if not username or not email or not password:
        return None
    return {
        "username": username,
        "email": email,
        "password": password,
    }


def _should_skip():
    return any(command in sys.argv for command in _skip_commands)


def _database_is_ready():
    try:
        connection = connections["default"]
        with connection.cursor():
            existing_tables = set(connection.introspection.table_names())
    except (OperationalError, ProgrammingError):
        return False

    user_table = get_user_model()._meta.db_table
    required_tables = {user_table, UserProfile._meta.db_table}
    return required_tables.issubset(existing_tables)


def ensure_default_superuser():
    global _bootstrap_attempted

    if _bootstrap_attempted or _should_skip():
        return

    credentials = _get_superuser_credentials()
    if not credentials:
        return

    with _bootstrap_lock:
        if _bootstrap_attempted:
            return

        if not _database_is_ready():
            return

        try:
            User = get_user_model()
            if User.objects.filter(is_superuser=True).exists():
                _bootstrap_attempted = True
                return

            user = User.objects.create_superuser(
                username=credentials["username"],
                email=credentials["email"],
                password=credentials["password"],
            )
            profile, _ = UserProfile.objects.get_or_create(user=user)
            if profile.role != UserProfile.ROLE_ADMIN:
                profile.role = UserProfile.ROLE_ADMIN
                profile.save(update_fields=["role"])
            _bootstrap_attempted = True
        except (OperationalError, ProgrammingError):
            return


def schedule_default_superuser_creation():
    global _bootstrap_scheduled

    if _bootstrap_scheduled or _should_skip():
        return

    _bootstrap_scheduled = True
    timer = Timer(0.1, ensure_default_superuser)
    timer.daemon = True
    timer.start()
