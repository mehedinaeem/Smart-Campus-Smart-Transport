from apps.core.decorators import role_required
from django.shortcuts import render

@role_required(
    "student",
    login_message="Please login to book a seat.",
    denied_message="Seat booking is available for student accounts only.",
)
def seat_booking_view(request):
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
        "route_name": "Green Line Express",
        "departure": "08:05 AM",
        "arrival": "08:28 AM",
        "seats": seats,
    }
    return render(request, "booking/seat_booking.html", context)
