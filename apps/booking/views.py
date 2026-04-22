from django.contrib import messages
from django.core.exceptions import ValidationError
from django.shortcuts import redirect, render
from django.urls import reverse

from apps.core.decorators import role_required

from .services import build_seat_layout, create_booking, get_available_assignments, get_user_active_booking


@role_required(
    "student",
    login_message="Please login to book a seat.",
    denied_message="Seat booking is available for student accounts only.",
)
def seat_booking_view(request):
    assignments = get_available_assignments()
    selected_assignment_id = request.GET.get("assignment")
    selected_assignment = None
    active_booking = get_user_active_booking(request.user)

    if request.method == "POST":
        assignment_id = request.POST.get("assignment_id")
        seat_number = request.POST.get("seat_number", "").strip().upper()

        if not assignment_id or not seat_number:
            messages.error(request, "Please choose a bus and seat before confirming your booking.")
            return redirect("seat-booking")

        selected_assignment = next((item for item in assignments if str(item.pk) == assignment_id), None)
        if not selected_assignment:
            messages.error(request, "This trip is not currently available for booking.")
            return redirect("seat-booking")

        try:
            booking = create_booking(user=request.user, assignment=selected_assignment, seat_number=seat_number)
        except ValidationError as exc:
            for errors in exc.message_dict.values():
                for error in errors:
                    messages.error(request, error)
            return redirect(f"{reverse('seat-booking')}?assignment={selected_assignment.pk}")
        except Exception:
            messages.error(request, "We could not complete your booking right now. Please try again.")
            return redirect(f"{reverse('seat-booking')}?assignment={selected_assignment.pk}")

        messages.success(request, f"Seat {booking.seat_number} is confirmed for {booking.assignment.bus.code}.")
        return redirect("my-booking")

    if assignments:
        if selected_assignment_id:
            selected_assignment = next(
                (assignment for assignment in assignments if str(assignment.pk) == selected_assignment_id),
                None,
            )
        selected_assignment = selected_assignment or assignments[0]

    seats = build_seat_layout(selected_assignment, request.user) if selected_assignment else []

    context = {
        "page_title": "Seat Booking",
        "page_name": "booking",
        "assignments": assignments,
        "selected_assignment": selected_assignment,
        "active_booking": active_booking,
        "route_name": selected_assignment.trip.route_label if selected_assignment else "No booking window is open",
        "departure": selected_assignment.trip.start_time.strftime("%I:%M %p") if selected_assignment else "--",
        "arrival": selected_assignment.trip.end_time.strftime("%I:%M %p") if selected_assignment else "--",
        "seats": seats,
    }
    return render(request, "booking/seat_booking.html", context)
