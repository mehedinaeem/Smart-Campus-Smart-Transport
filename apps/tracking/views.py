from django.shortcuts import render

from apps.routing.services import get_live_assignments


def live_tracking_view(request):
    assignments = get_live_assignments()
    selected_assignment_id = request.GET.get("assignment")
    selected_assignment = None
    driver_name = "Unassigned"

    if assignments:
        if selected_assignment_id:
            selected_assignment = next(
                (assignment for assignment in assignments if str(assignment.pk) == selected_assignment_id),
                None,
            )
        selected_assignment = selected_assignment or assignments[0]
        if selected_assignment.driver:
            driver_name = selected_assignment.driver.get_full_name() or selected_assignment.driver.username

    context = {
        "page_title": "Live Tracking",
        "page_name": "tracking",
        "assignments": assignments,
        "selected_assignment": selected_assignment,
        "trip": {
            "route": selected_assignment.trip.route_label if selected_assignment else "No active or upcoming trips",
            "driver": driver_name,
            "bus_id": selected_assignment.bus.code if selected_assignment else "--",
            "speed": "32 km/h" if selected_assignment else "--",
            "eta": selected_assignment.trip.start_time.strftime("%I:%M %p") if selected_assignment else "--",
            "status": selected_assignment.trip.status_label if selected_assignment else "Unavailable",
        },
        "stops": [
            "Research Block",
            "Business School",
            "Main Cafeteria",
            "North Dorm",
            "Sports Complex",
        ],
    }
    return render(request, "tracking/live_tracking.html", context)
