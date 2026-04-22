import json

from django.http import JsonResponse
from django.shortcuts import render
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_GET, require_POST

from .services import TrackingError, get_tracking_dashboard_payload, ingest_device_telemetry


def live_tracking_view(request):
    selected_assignment_id = request.GET.get("assignment")
    try:
        selected_assignment_id = int(selected_assignment_id) if selected_assignment_id else None
    except (TypeError, ValueError):
        selected_assignment_id = None

    tracking_payload = get_tracking_dashboard_payload(selected_assignment_id=selected_assignment_id)
    context = {
        "page_title": "Live Tracking",
        "page_name": "tracking",
        "tracking_payload": tracking_payload,
        "selected_vehicle": tracking_payload["selected_vehicle"],
    }
    return render(request, "tracking/live_tracking.html", context)


@require_GET
def live_tracking_feed_view(request):
    selected_assignment_id = request.GET.get("assignment")
    try:
        selected_assignment_id = int(selected_assignment_id) if selected_assignment_id else None
    except (TypeError, ValueError):
        selected_assignment_id = None

    return JsonResponse(get_tracking_dashboard_payload(selected_assignment_id=selected_assignment_id))


@csrf_exempt
@require_POST
def telemetry_ingest_view(request):
    try:
        payload = json.loads(request.body.decode("utf-8"))
    except (json.JSONDecodeError, UnicodeDecodeError):
        return JsonResponse({"ok": False, "error": "Request body must be valid JSON."}, status=400)

    try:
        result = ingest_device_telemetry(payload)
    except TrackingError as exc:
        return JsonResponse({"ok": False, "error": str(exc)}, status=400)

    return JsonResponse(result, status=201)
