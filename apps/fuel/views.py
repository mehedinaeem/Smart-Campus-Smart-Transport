from django.shortcuts import render

def alerts_monitoring_view(request):
    context = {
        "page_title": "Alerts & Monitoring",
        "page_name": "alerts",
        "alerts": [
            {"level": "critical", "title": "Fuel variance detected", "detail": "BUS-11 exceeded expected consumption by 18% on the Medical Shuttle route."},
            {"level": "warning", "title": "Traffic pressure rising", "detail": "South Gate corridor moved to heavy congestion for the next 25 minutes."},
            {"level": "success", "title": "Route health stable", "detail": "North Loop completed 14 uninterrupted trips with no late arrivals."},
            {"level": "info", "title": "Sensor sync restored", "detail": "Real-time telemetry resumed for BUS-06 after a 2-minute packet loss."},
        ],
    }
    return render(request, "fuel/alerts_monitoring.html", context)
