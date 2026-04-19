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


def analytics_view(request):
    context = {
        "page_title": "Analytics",
        "page_name": "analytics",
        "insight_cards": [
            {"label": "Avg Occupancy", "value": "74%", "detail": "Morning peak remains the busiest period"},
            {"label": "On-Time Rate", "value": "93.4%", "detail": "Up 4.1% over last week"},
            {"label": "Alert Resolution", "value": "18 min", "detail": "Mean response time across active routes"},
        ],
        "insight_rows": [
            {"title": "Route Demand", "detail": "North Loop and Dorm Express are driving most seat bookings this week."},
            {"title": "Fuel Efficiency", "detail": "Electric fleet zones show the strongest efficiency during afternoon rotations."},
            {"title": "Operational Risk", "detail": "Two congestion clusters are affecting the Medical Shuttle corridor."},
        ],
    }
    return render(request, "dashboard/analytics.html", context)
