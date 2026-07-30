from django.urls import path
from . import views

urlpatterns = [

    path(
        '',
        views.ticket_booking,
        name='ticket_booking'
    ),

    path(
        'select-seat/<int:train_id>/',
        views.select_seat,
        name='select_seat'
    ),

    path(
        'booking-summary/',
        views.booking_summary,
        name='booking_summary'
    ),
    path(
    'confirm-booking/',
    views.confirm_booking,
    name='confirm_booking'
    ),
    
    path(
    'payment/<int:booking_id>/',
    views.payment,
    name='payment'
),

]