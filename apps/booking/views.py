from apps.core.decorators import role_required
from django.shortcuts import render

from apps.routing.services import get_booking_assignments


@role_required(
    "student",
    login_message="Please login to book a seat.",
    denied_message="Seat booking is available for student accounts only.",
)
def seat_booking_view(request):
    assignments = get_booking_assignments()
    selected_assignment_id = request.GET.get("assignment")
    selected_assignment = None

    if assignments:
        if selected_assignment_id:
            selected_assignment = next(
                (assignment for assignment in assignments if str(assignment.pk) == selected_assignment_id),
                None,
            )
        selected_assignment = selected_assignment or assignments[0]

    seats = []
    booked = {"A2", "A4", "B1", "B5", "C3", "C4", "D2", "D6"}
    premium = {"A1", "A3", "B2", "B4"}

    for row in ["A", "B", "C", "D", "E"]:
        for col in range(1, 7):
            code = f"{row}{col}"
            seats.append(
                {
                    "code": code,
                    "state": "booked" if code in booked else "premium" if code in premium else "available",
                }
            )

    context = {
        "page_title": "Seat Booking",
        "page_name": "booking",
        "assignments": assignments,
        "selected_assignment": selected_assignment,
        "route_name": selected_assignment.trip.route_label if selected_assignment else "No booking window is open",
        "departure": selected_assignment.trip.start_time.strftime("%I:%M %p") if selected_assignment else "--",
        "arrival": selected_assignment.trip.end_time.strftime("%I:%M %p") if selected_assignment else "--",
        "seats": seats,
    }
    return render(request, "booking/seat_booking.html", context)
