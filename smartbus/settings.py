import os
import socket
from pathlib import Path

import environ
from django.core.exceptions import ImproperlyConfigured

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent
env = environ.Env(
    DEBUG=(bool, False),
    EMAIL_PORT=(int, 587),
    EMAIL_USE_TLS=(bool, True),
    TRACKING_ONLINE_WINDOW_SECONDS=(int, 75),
    TRACKING_OFFLINE_WINDOW_SECONDS=(int, 240),
    TRACKING_SNAPSHOT_INTERVAL_SECONDS=(int, 60),
    DB_CONN_MAX_AGE=(int, 600),
    SECURE_SSL_REDIRECT=(bool, True),
    SECURE_HSTS_SECONDS=(int, 31536000),
    SECURE_HSTS_INCLUDE_SUBDOMAINS=(bool, True),
    SECURE_HSTS_PRELOAD=(bool, True),
)
environ.Env.read_env(BASE_DIR / ".env")


def _env_list(name, default=None):
    return [item.strip() for item in env.list(name, default=default or []) if item.strip()]


DEBUG = env("DEBUG")
SECRET_KEY = env("SECRET_KEY", default="")
if not SECRET_KEY:
    if DEBUG:
        SECRET_KEY = "dev-only-secret-key-change-me"
    else:
        raise ImproperlyConfigured("SECRET_KEY must be set when DEBUG is False.")


def _development_hosts():
    hosts = {"127.0.0.1", "localhost", "0.0.0.0", "::1"}

    for candidate in (socket.gethostname(), socket.getfqdn()):
        if candidate:
            hosts.add(candidate)

    try:
        hosts.update(socket.gethostbyname_ex(socket.gethostname())[2])
    except OSError:
        pass

    try:
        for family, _, _, _, sockaddr in socket.getaddrinfo(socket.gethostname(), None):
            if family in (socket.AF_INET, socket.AF_INET6) and sockaddr:
                hosts.add(sockaddr[0])
    except OSError:
        pass

    return hosts


RENDER_EXTERNAL_HOSTNAME = env("RENDER_EXTERNAL_HOSTNAME", default="")

ALLOWED_HOSTS = set(_env_list("ALLOWED_HOSTS", default=["127.0.0.1", "localhost"]))
if RENDER_EXTERNAL_HOSTNAME:
    ALLOWED_HOSTS.add(RENDER_EXTERNAL_HOSTNAME)
if DEBUG:
    ALLOWED_HOSTS.update(_development_hosts())
ALLOWED_HOSTS = sorted(ALLOWED_HOSTS)

CSRF_TRUSTED_ORIGINS = _env_list("CSRF_TRUSTED_ORIGINS")
if RENDER_EXTERNAL_HOSTNAME:
    CSRF_TRUSTED_ORIGINS.append(f"https://{RENDER_EXTERNAL_HOSTNAME}")
CSRF_TRUSTED_ORIGINS = sorted(set(CSRF_TRUSTED_ORIGINS))


INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'apps.core',
    'apps.dashboard',
    'apps.booking',
    'apps.tracking',
    'apps.fuel',
    'apps.routing',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'smartbus.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / 'templates'],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
                'apps.core.context_processors.auth_ui',
            ],
        },
    },
]

WSGI_APPLICATION = 'smartbus.wsgi.application'


default_sqlite_url = f"sqlite:///{BASE_DIR.joinpath('db.sqlite3').as_posix()}"
DATABASES = {
    'default': env.db("DATABASE_URL", default=default_sqlite_url)
}
DATABASES["default"]["CONN_MAX_AGE"] = env("DB_CONN_MAX_AGE")
DATABASES["default"]["CONN_HEALTH_CHECKS"] = True


AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
    },
]


LANGUAGE_CODE = 'en-us'

TIME_ZONE = 'Asia/Dhaka'

USE_I18N = True

USE_TZ = True


STATIC_URL = '/static/'
STATICFILES_DIRS = [BASE_DIR / 'static']
STATIC_ROOT = BASE_DIR / 'staticfiles'
STORAGES = {
    "default": {
        "BACKEND": "django.core.files.storage.FileSystemStorage",
    },
    "staticfiles": {
        "BACKEND": "whitenoise.storage.CompressedManifestStaticFilesStorage",
    },
}
WHITENOISE_MAX_AGE = 31536000 if not DEBUG else 0

LOGIN_URL = 'login'
LOGIN_REDIRECT_URL = 'student-dashboard'
LOGOUT_REDIRECT_URL = 'student-dashboard'

EMAIL_BACKEND = env("EMAIL_BACKEND", default="django.core.mail.backends.console.EmailBackend")
EMAIL_HOST = env("EMAIL_HOST", default="localhost")
EMAIL_PORT = env("EMAIL_PORT")
EMAIL_HOST_USER = env("EMAIL_HOST_USER", default="")
EMAIL_HOST_PASSWORD = env("EMAIL_HOST_PASSWORD", default="")
EMAIL_USE_TLS = env("EMAIL_USE_TLS")
DEFAULT_FROM_EMAIL = env("DEFAULT_FROM_EMAIL", default="Smart Campus <no-reply@smartcampus.local>")
TRACKING_SHARED_API_KEY = env("TRACKING_SHARED_API_KEY", default="")
TRACKING_ONLINE_WINDOW_SECONDS = env("TRACKING_ONLINE_WINDOW_SECONDS")
TRACKING_OFFLINE_WINDOW_SECONDS = env("TRACKING_OFFLINE_WINDOW_SECONDS")
TRACKING_SNAPSHOT_INTERVAL_SECONDS = env("TRACKING_SNAPSHOT_INTERVAL_SECONDS")

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

if not DEBUG:
    SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
    SECURE_SSL_REDIRECT = env("SECURE_SSL_REDIRECT")
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True
    SECURE_CONTENT_TYPE_NOSNIFF = True
    SECURE_HSTS_SECONDS = env("SECURE_HSTS_SECONDS")
    SECURE_HSTS_INCLUDE_SUBDOMAINS = env("SECURE_HSTS_INCLUDE_SUBDOMAINS")
    SECURE_HSTS_PRELOAD = env("SECURE_HSTS_PRELOAD")
else:
    SECURE_SSL_REDIRECT = False
