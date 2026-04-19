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
from apps.core.views import student_dashboard_view
from apps.dashboard.views import admin_dashboard_view, analytics_view
from apps.fuel.views import alerts_monitoring_view
from apps.routing.views import bus_schedule_view
from apps.tracking.views import live_tracking_view

urlpatterns = [
    path('system-admin/', admin.site.urls),
    path('', student_dashboard_view, name='student-dashboard'),
    path('booking/', seat_booking_view, name='seat-booking'),
    path('tracking/', live_tracking_view, name='live-tracking'),
    path('schedule/', bus_schedule_view, name='bus-schedule'),
    path('admin/', admin_dashboard_view, name='admin-dashboard'),
    path('alerts/', alerts_monitoring_view, name='alerts-monitoring'),
    path('analytics/', analytics_view, name='analytics'),
]
