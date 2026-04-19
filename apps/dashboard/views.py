from django.shortcuts import render

def admin_dashboard_view(request):
    context = {
        "page_title": "Admin Dashboard",
        "page_name": "admin",
        "summary_cards": [
            {"label": "Active Buses", "value": "24", "delta": "+3 online"},
            {"label": "Trips Today", "value": "118", "delta": "+12% vs yesterday"},
            {"label": "Total Bookings", "value": "2,431", "delta": "92% seat utilization"},
            {"label": "Alerts", "value": "07", "delta": "2 require action"},
        ],
        "trips": [
            {"route": "North Loop", "bus": "BUS-04", "status": "Running", "load": "71%", "eta": "3 min"},
            {"route": "Medical Shuttle", "bus": "BUS-11", "status": "Delayed", "load": "52%", "eta": "11 min"},
            {"route": "Dorm Express", "bus": "BUS-08", "status": "Running", "load": "88%", "eta": "6 min"},
            {"route": "Library Connector", "bus": "BUS-17", "status": "Charging", "load": "0%", "eta": "24 min"},
        ],
    }
    return render(request, "dashboard/admin_dashboard.html", context)
