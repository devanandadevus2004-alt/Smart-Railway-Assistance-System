import json
from django.shortcuts import (
    render,
    redirect,
    get_object_or_404
)

from home.models import (
    Station,
    Passenger
)

from .models import (
    Train,
    TrainStop,
    Coach,
    Seat,
     TicketBooking

)



def ticket_booking(request):

    stations = Station.objects.all().order_by('station_name')

    trains = None
    travel_date = None
    source_id = None
    destination_id = None

    if request.method == 'POST':

        source_id = request.POST.get('source_station')
        destination_id = request.POST.get('destination_station')
        travel_date = request.POST.get('travel_date')

        # Store selected journey details in session
        request.session['source_station_id'] = source_id
        request.session['destination_station_id'] = destination_id
        request.session['travel_date'] = travel_date

        if source_id and destination_id:

            # Get all train stops for the selected source station
            source_stops = TrainStop.objects.filter(
                station_id=source_id
            )

            # Get all train stops for the selected destination station
            destination_stops = TrainStop.objects.filter(
                station_id=destination_id
            )

            # Store destination stop order by train
            destination_orders = {}

            for stop in destination_stops:
                destination_orders[stop.train_id] = stop.stop_order

            # Find trains where source comes before destination
            valid_train_ids = []

            for source_stop in source_stops:

                destination_order = destination_orders.get(
                    source_stop.train_id
                )

                if destination_order is not None:

                    if source_stop.stop_order < destination_order:

                        valid_train_ids.append(
                            source_stop.train_id
                        )

            # Get the actual Train objects
            trains = Train.objects.filter(
                id__in=valid_train_ids,
                is_active=True
            )

    return render(
        request,
        'ticket_booking/ticket_booking.html',
        {
            'stations': stations,
            'trains': trains,
            'travel_date': travel_date,
        }
    )


def select_seat(request, train_id):

    train = get_object_or_404(
        Train,
        id=train_id
    )

    source_id = request.session.get('source_station_id')
    destination_id = request.session.get('destination_station_id')
    travel_date = request.session.get('travel_date')

    travel_date = request.GET.get(
        'travel_date'
    )

    coaches = Coach.objects.filter(
        train=train,
    ).prefetch_related('seats')

    # Prepare coach and seat data
    coaches_data = []

    for coach in coaches:

        seats_data = []

        for seat in coach.seats.all():

            seats_data.append({
                'id': seat.id,
                'seat_number': seat.seat_number,
                'seat_type': seat.get_seat_type_display(),
                'is_active': seat.is_active,
            })

        coaches_data.append({
            'id': coach.id,
            'coach_number': coach.coach_number,
            'coach_type': coach.coach_type,
            'is_bookable': coach.is_bookable,
            'seats': seats_data,
        })

    return render(
        request,
        'ticket_booking/select_seat.html',
        {
            'train': train,
            'coaches': coaches,
            'coaches_json': json.dumps(
                coaches_data
            ),
            'travel_date': travel_date,
        }
    )

    

def booking_summary(request):

    train_id = request.GET.get('train_id')
    seat_id = request.GET.get('seat_id')
    travel_date = request.GET.get('travel_date')

    # Get logged-in passenger
    passenger_id = request.session.get('passenger_id')

    # User must be logged in
    if not passenger_id:
        return redirect('login')

    # Get train
    train = get_object_or_404(
        Train,
        id=train_id
    )

    # Get selected seat
    seat = get_object_or_404(
        Seat,
        id=seat_id
    )

    # Get passenger
    passenger = get_object_or_404(
        Passenger,
        id=passenger_id
    )

    return render(
        request,
        'ticket_booking/booking_summary.html',
        {
            'train': train,
            'seat': seat,
            'passenger': passenger,
            'travel_date': travel_date,
        }
    )


def confirm_booking(request):

    if request.method != 'POST':
        return redirect('ticket_booking')

    # Get passenger from session
    passenger_id = request.session.get(
        'passenger_id'
    )

    if not passenger_id:
        return redirect('login')

    passenger = get_object_or_404(
        Passenger,
        id=passenger_id
    )

    # Get submitted data
    train_id = request.POST.get(
        'train_id'
    )

    seat_id = request.POST.get(
        'seat_id'
    )

    travel_date = request.POST.get(
        'travel_date'
    )

    # Get train and seat
    train = get_object_or_404(
        Train,
        id=train_id
    )

    seat = get_object_or_404(
        Seat,
        id=seat_id
    )

    # Create pending booking
    booking = TicketBooking.objects.create(

        passenger=passenger,

        train=train,

        seat=seat,

        travel_date=travel_date,

        fare=0,

        status='PENDING'
    )

    # Go to payment page
    return redirect(
        'payment',
        booking_id=booking.id
    )

def payment(request, booking_id):

    booking = get_object_or_404(
        TicketBooking,
        id=booking_id
    )

    return render(
        request,
        'ticket_booking/payment.html',
        {
            'booking': booking,
        }
    )