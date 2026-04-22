"""
URL configuration for smartbus project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/4.2/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path
from apps.booking.views import seat_booking_view
from apps.core.views import (
    RoleAwareLoginView,
    RoleAwareLogoutView,
    StudentSignupView,
    driver_dashboard_view,
    my_booking_view,
    student_dashboard_view,
)
from apps.dashboard.views import admin_dashboard_view, analytics_view, manage_roles_view, trip_assignments_view
from apps.fuel.views import alerts_monitoring_view
from apps.routing.views import bus_schedule_view
from apps.tracking.views import live_tracking_feed_view, live_tracking_view, telemetry_ingest_view

urlpatterns = [
    path('system-admin/', admin.site.urls),
    path('', student_dashboard_view, name='student-dashboard'),
    path('login/', RoleAwareLoginView.as_view(), name='login'),
    path('logout/', RoleAwareLogoutView.as_view(), name='logout'),
    path('signup/', StudentSignupView.as_view(), name='signup'),
    path('booking/', seat_booking_view, name='seat-booking'),
    path('my-booking/', my_booking_view, name='my-booking'),
    path('tracking/', live_tracking_view, name='live-tracking'),
    path('api/tracking/live/', live_tracking_feed_view, name='live-tracking-feed'),
    path('api/device/telemetry/', telemetry_ingest_view, name='telemetry-ingest'),
    path('driver/', driver_dashboard_view, name='driver-dashboard'),
    path('schedule/', bus_schedule_view, name='bus-schedule'),
    path('admin/', admin_dashboard_view, name='admin-dashboard'),
    path('admin/trips/', trip_assignments_view, name='trip-assignments'),
    path('admin/roles/', manage_roles_view, name='manage-roles'),
    path('alerts/', alerts_monitoring_view, name='alerts-monitoring'),
    path('analytics/', analytics_view, name='analytics'),
]