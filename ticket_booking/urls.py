from django.urls import path
from . import views

urlpatterns = [

    # ========================================================
    # TRAIN SEARCH
    # ========================================================

    path(
        '',
        views.ticket_booking,
        name='ticket_booking'
    ),

    # ========================================================
    # PASSENGER REQUIREMENTS
    # User enters number of passengers and preferences
    # ========================================================

    path(
        'passenger-requirements/<int:train_id>/',
        views.passenger_requirements,
        name='passenger_requirements'
    ),



    # ========================================================
# PASSENGER DETAILS AND PREFERENCES
# User enters details for each passenger
# ========================================================

path(
    'passenger-details/<int:train_id>/',
    views.passenger_details,
    name='passenger_details'
),

    # ========================================================
    # SEAT ALLOCATION ALGORITHM
    # Algorithm finds the best coach and seats
    # ========================================================

    path(
        'seat-recommendation/<int:train_id>/',
        views.seat_recommendation,
        name='seat_recommendation'
    ),

    # ========================================================
    # BOOKING SUMMARY
    # ========================================================

    path(
        'booking-summary/',
        views.booking_summary,
        name='booking_summary'
    ),

    # ========================================================
    # CONFIRM BOOKING
    # ========================================================

    path(
        'confirm-booking/',
        views.confirm_booking,
        name='confirm_booking'
    ),

    # ========================================================
    # PAYMENT
    # ========================================================

    path(
        'payment/<int:booking_id>/',
        views.payment,
        name='payment'
    ),

    path(
    'multiple-booking-summary/',
    views.multiple_booking_summary,
    name='multiple_booking_summary'
    ),

    path(
    'create-multiple-booking/',
    views.create_multiple_booking,
    name='create_multiple_booking'
),

path(
    "seat-conflict/",
    views.seat_conflict,
    name="seat_conflict"
),

path(
    "allocation-strategy/",
    views.save_allocation_strategy,
    name="save_allocation_strategy"
),

path(
    "continue-group-booking/",
    views.continue_group_booking,
    name="continue_group_booking"
),

path(
    "allocation-result/",
    views.allocation_result,
    name="allocation_result"
),

path(
    "keep-group-together/",
    views.keep_group_together,
    name="keep_group_together",
),

path(
    "prioritize-lower-berths/",
    views.prioritize_lower_berths,
    name="prioritize_lower_berths",
),


path(
    'payment/process/<int:booking_id>/',
    views.process_payment,
    name='process_payment'
),

path(
    "my-ticket-bookings/",
    views.my_ticket_bookings,
    name="my_ticket_bookings",
),


path(
    "ticket-booking-details/<int:booking_id>/",
    views.ticket_booking_details,
    name="ticket_booking_details",
),
]