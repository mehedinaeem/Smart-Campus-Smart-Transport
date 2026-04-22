from django.shortcuts import render

from apps.core.decorators import role_required

from .services import build_alert_summary, filter_operational_alerts, generate_operational_alerts, get_alert_filter_options


@role_required(
    "admin",
    login_message="Please login to access alerts and monitoring.",
    denied_message="Admin access is required for alerts and monitoring.",
)
def alerts_monitoring_view(request):
    filters = {
        "q": request.GET.get("q", "").strip(),
        "severity": request.GET.get("severity", "").strip(),
        "type": request.GET.get("type", "").strip(),
        "status": request.GET.get("status", "").strip(),
        "route": request.GET.get("route", "").strip(),
        "bus": request.GET.get("bus", "").strip(),
    }

    all_alerts = generate_operational_alerts()
    filtered_alerts = filter_operational_alerts(alerts=all_alerts, filters=filters)
    filter_options = get_alert_filter_options()
    active_filter_count = sum(1 for value in filters.values() if value)

    context = {
        "page_title": "Alerts & Monitoring",
        "page_name": "alerts",
        "alerts": filtered_alerts,
        "filters": filters,
        "summary": build_alert_summary(all_alerts),
        "matched_alert_count": len(filtered_alerts),
        "active_filter_count": active_filter_count,
        **filter_options,
    }
    return render(request, "fuel/alerts_monitoring.html", context)
