from django.shortcuts import render

from .services import get_schedule_page_content


def bus_schedule_view(request):
    context = {
        "page_title": "Bus Schedule",
        "page_name": "schedule",
        **get_schedule_page_content(),
    }
    return render(request, "routing/bus_schedule.html", context)
