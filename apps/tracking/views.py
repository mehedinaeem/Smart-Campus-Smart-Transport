from django.shortcuts import render

def live_tracking_view(request):
    context = {
        "page_title": "Live Tracking",
        "page_name": "tracking",
        "trip": {
            "route": "Campus Link South",
            "driver": "Mahmud Rahman",
            "bus_id": "BUS-17",
            "speed": "32 km/h",
            "eta": "6 min",
            "status": "On Schedule",
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
