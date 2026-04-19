from django.shortcuts import render


def bus_schedule_view(request):
    context = {
        "page_title": "Bus Schedule",
        "page_name": "schedule",
        "hero_schedule": {
            "line": "Green Loop Express",
            "window": "Peak service active from 7:30 AM to 10:00 AM",
            "cadence": "Every 8 minutes",
        },
        "schedule_cards": [
            {"label": "First Departure", "value": "07:30 AM", "detail": "Residence Hall Terminal"},
            {"label": "Next Arrival", "value": "08:12 AM", "detail": "Central Library stop"},
            {"label": "Last Campus Loop", "value": "09:45 PM", "detail": "Innovation Hub return"},
        ],
        "departures": [
            {"route": "North Loop", "stop": "Engineering Gate", "time": "08:05 AM", "status": "On Time"},
            {"route": "Library Connector", "stop": "Central Library", "time": "08:12 AM", "status": "Boarding"},
            {"route": "Medical Shuttle", "stop": "Health Center", "time": "08:18 AM", "status": "On Time"},
            {"route": "Dorm Express", "stop": "Dormitory West", "time": "08:24 AM", "status": "Delayed"},
        ],
        "route_notes": [
            "Seat reservations open 10 minutes before each departure window.",
            "Boarding zones are color-matched with the route label for faster wayfinding.",
            "Login unlocks student booking tools or role-specific workspaces based on your account.",
        ],
    }
    return render(request, "routing/bus_schedule.html", context)
