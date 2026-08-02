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

]