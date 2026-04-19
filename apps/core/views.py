from django.shortcuts import render

def student_dashboard_view(request):
    context = {
        "page_title": "Student Dashboard",
        "page_name": "dashboard",
        "live_status": {
            "bus": "Campus Loop A2",
            "location": "Near Engineering Gate",
            "eta": "4 min",
            "traffic": "Normal",
            "next_arrival": "08:12 AM",
            "occupancy": "18 / 32 seats",
        },
        "stops": [
            {"name": "Innovation Hub", "eta": "2 min"},
            {"name": "Central Library", "eta": "4 min"},
            {"name": "Dormitory West", "eta": "8 min"},
            {"name": "Medical Center", "eta": "12 min"},
        ],
    }
    return render(request, "core/student_dashboard.html", context)
