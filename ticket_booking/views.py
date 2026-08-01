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
    TrainStopDistance,
    Coach,
    Seat,
    TicketBooking,
    BookingPassenger,
    SeatReservation
)

from .fare_calculator import calculate_fare


# ============================================================
# HELPER FUNCTION
# GET JOURNEY DISTANCE
# ============================================================

def get_journey_distance(
    train,
    source_id,
    destination_id
):

    # --------------------------------------------------------
    # Try to find actual imported distance
    # --------------------------------------------------------

    distance_record = (
        TrainStopDistance.objects.filter(

            train=train,

            source_station_id=source_id,

            destination_station_id=destination_id

        )
        .first()
    )

    # --------------------------------------------------------
    # Actual distance available
    # --------------------------------------------------------

    if distance_record:

        return {

            "distance":
                distance_record.distance,

            "distance_source":
                "Actual",

            "stop_segments":
                None

        }

    # --------------------------------------------------------
    # Actual distance unavailable
    # Use stop count as fallback
    # --------------------------------------------------------

    source_stop = (
        TrainStop.objects.filter(

            train=train,

            station_id=source_id

        )
        .first()
    )

    destination_stop = (
        TrainStop.objects.filter(

            train=train,

            station_id=destination_id

        )
        .first()
    )

    # --------------------------------------------------------
    # If both stops exist
    # --------------------------------------------------------

    if source_stop and destination_stop:

        stop_segments = (

            destination_stop.stop_order

            -

            source_stop.stop_order

        )

        if stop_segments < 0:

            stop_segments = 0

    else:

        stop_segments = 0

    return {

        "distance":
            None,

        "distance_source":
            "Estimated",

        "stop_segments":
            stop_segments

    }


# ============================================================
# TICKET BOOKING / TRAIN SEARCH
# ============================================================

def ticket_booking(request):

    stations = (
        Station.objects
        .all()
        .order_by(
            'station_name'
        )
    )

    trains = None

    travel_date = None

    source_id = None

    destination_id = None

    if request.method == 'POST':

        source_id = request.POST.get(
            'source_station'
        )

        destination_id = request.POST.get(
            'destination_station'
        )

        travel_date = request.POST.get(
            'travel_date'
        )

        # ----------------------------------------------------
        # Store journey details in session
        # ----------------------------------------------------

        request.session[
            'source_station_id'
        ] = source_id

        request.session[
            'destination_station_id'
        ] = destination_id

        request.session[
            'travel_date'
        ] = travel_date

        # ----------------------------------------------------
        # Check source and destination
        # ----------------------------------------------------

        if source_id and destination_id:

            # ------------------------------------------------
            # Get source stops
            # ------------------------------------------------

            source_stops = (
                TrainStop.objects.filter(
                    station_id=source_id
                )
            )

            # ------------------------------------------------
            # Get destination stops
            # ------------------------------------------------

            destination_stops = (
                TrainStop.objects.filter(
                    station_id=destination_id
                )
            )

            # ------------------------------------------------
            # Store destination order
            # ------------------------------------------------

            destination_orders = {}

            for stop in destination_stops:

                destination_orders[
                    stop.train_id
                ] = stop.stop_order

            # ------------------------------------------------
            # Find valid trains
            # ------------------------------------------------

            valid_train_ids = []

            for source_stop in source_stops:

                destination_order = (
                    destination_orders.get(
                        source_stop.train_id
                    )
                )

                if destination_order is not None:

                    if (
                        source_stop.stop_order
                        <
                        destination_order
                    ):

                        valid_train_ids.append(
                            source_stop.train_id
                        )

            # ------------------------------------------------
            # Get trains
            # ------------------------------------------------

            trains = (
                Train.objects.filter(

                    id__in=valid_train_ids,

                    is_active=True

                )
            )

    return render(

        request,

        'ticket_booking/ticket_booking.html',

        {

            'stations':
                stations,

            'trains':
                trains,

            'travel_date':
                travel_date,

        }

    )


# ============================================================
# SELECT SEAT
# ============================================================

def select_seat(
    request,
    train_id
):

    # --------------------------------------------------------
    # Get train
    # --------------------------------------------------------

    train = get_object_or_404(
        Train,
        id=train_id
    )

    # --------------------------------------------------------
    # Get session journey details
    # --------------------------------------------------------

    source_id = request.session.get(
        'source_station_id'
    )

    destination_id = request.session.get(
        'destination_station_id'
    )

    travel_date = request.session.get(
        'travel_date'
    )

    # --------------------------------------------------------
    # Allow travel date from URL
    # --------------------------------------------------------

    travel_date = request.GET.get(
        'travel_date',
        travel_date
    )

    # --------------------------------------------------------
    # Get coaches for selected train
    #
    # Only load required fields.
    # --------------------------------------------------------

    coaches = (
        Coach.objects
        .filter(
            train_id=train_id,
            is_bookable=True
        )
        .only(
            'id',
            'coach_number',
            'coach_type',
            'is_bookable'
        )
        .prefetch_related(
            'seats'
        )
        .order_by(
            'id'
        )
    )

    # --------------------------------------------------------
    # Prepare JSON data for JavaScript
    # --------------------------------------------------------

    coaches_data = []

    for coach in coaches:

        seats_data = []

        # ----------------------------------------------------
        # Get seats belonging to this coach
        # ----------------------------------------------------

        for seat in coach.seats.all():

            seats_data.append({

                'id':
                    seat.id,

                'seat_number':
                    seat.seat_number,

                'seat_type':
                    seat.get_seat_type_display(),

                'is_active':
                    seat.is_active,

            })

        # ----------------------------------------------------
        # Add coach information
        # ----------------------------------------------------

        coaches_data.append({

            'id':
                coach.id,

            'coach_number':
                coach.coach_number,

            'coach_type':
                coach.coach_type,

            'is_bookable':
                coach.is_bookable,

            'seats':
                seats_data,

        })

    # --------------------------------------------------------
    # Render select seat page
    # --------------------------------------------------------

    return render(

        request,

        'ticket_booking/select_seat.html',

        {

            'train':
                train,

            'coaches':
                coaches,

            'coaches_json':
                json.dumps(
                    coaches_data
                ),

            'travel_date':
                travel_date,

        }

    )


# ============================================================
# BOOKING SUMMARY
# ============================================================

def booking_summary(request):

    train_id = request.GET.get(
        'train_id'
    )

    seat_id = request.GET.get(
        'seat_id'
    )

    travel_date = request.GET.get(
        'travel_date'
    )

    # --------------------------------------------------------
    # Get logged-in passenger
    # --------------------------------------------------------

    passenger_id = (
        request.session.get(
            'passenger_id'
        )
    )

    # --------------------------------------------------------
    # Login required
    # --------------------------------------------------------

    if not passenger_id:

        return redirect(
            'login'
        )

    # --------------------------------------------------------
    # Get train
    # --------------------------------------------------------

    train = get_object_or_404(

        Train,

        id=train_id

    )

    # --------------------------------------------------------
    # Get selected seat
    # --------------------------------------------------------

    seat = get_object_or_404(

        Seat,

        id=seat_id

    )

    # --------------------------------------------------------
    # Get logged-in passenger
    # --------------------------------------------------------

    passenger = get_object_or_404(

        Passenger,

        id=passenger_id

    )

    # --------------------------------------------------------
    # Get source and destination
    # --------------------------------------------------------

    source_id = request.session.get(

        'source_station_id'

    )

    destination_id = request.session.get(

        'destination_station_id'

    )

    # --------------------------------------------------------
    # Get journey distance
    # --------------------------------------------------------

    journey_data = get_journey_distance(

        train=train,

        source_id=source_id,

        destination_id=destination_id

    )

    # --------------------------------------------------------
    # Get coach type
    # --------------------------------------------------------

    coach_type = (

        seat.coach.coach_type

    )

    # --------------------------------------------------------
    # Calculate fare
    # --------------------------------------------------------

    fare_data = calculate_fare(

        distance=
            journey_data[
                'distance'
            ],

        stop_segments=
            journey_data[
                'stop_segments'
            ],

        coach_type=
            coach_type

    )

    # --------------------------------------------------------
    # Get actual source station
    # --------------------------------------------------------

    source_station = get_object_or_404(

        Station,

        id=source_id

    )

    # --------------------------------------------------------
    # Get actual destination station
    # --------------------------------------------------------

    destination_station = get_object_or_404(

        Station,

        id=destination_id

    )

    # --------------------------------------------------------
    # Render booking summary
    # --------------------------------------------------------

    return render(

        request,

        'ticket_booking/booking_summary.html',

        {

            'train':
                train,

            'seat':
                seat,

            'passenger':
                passenger,

            'travel_date':
                travel_date,

            'source_station':
                source_station,

            'destination_station':
                destination_station,

            'distance':
                fare_data[
                    'distance'
                ],

            'distance_source':
                fare_data[
                    'distance_source'
                ],

            'coach_type':
                coach_type,

            'base_fare':
                fare_data[
                    'base_fare'
                ],

            'reservation_charge':
                fare_data[
                    'reservation_charge'
                ],

            'superfast_charge':
                fare_data[
                    'superfast_charge'
                ],

            'total_fare':
                fare_data[
                    'total_fare'
                ],

        }

    )


# ============================================================
# CONFIRM BOOKING
# ============================================================

def confirm_booking(request):

    if request.method != 'POST':

        return redirect(
            'ticket_booking'
        )

    # --------------------------------------------------------
    # Get logged-in passenger
    # --------------------------------------------------------

    passenger_id = request.session.get(
        'passenger_id'
    )

    if not passenger_id:

        return redirect(
            'login'
        )

    passenger = get_object_or_404(

        Passenger,

        id=passenger_id

    )

    # --------------------------------------------------------
    # Get submitted values
    # --------------------------------------------------------

    train_id = request.POST.get(

        'train_id'

    )

    seat_id = request.POST.get(

        'seat_id'

    )

    travel_date = request.POST.get(

        'travel_date'

    )

    # --------------------------------------------------------
    # Get train
    # --------------------------------------------------------

    train = get_object_or_404(

        Train,

        id=train_id

    )

    # --------------------------------------------------------
    # Get selected seat
    # --------------------------------------------------------

    seat = get_object_or_404(

        Seat,

        id=seat_id

    )

    # --------------------------------------------------------
    # Get source and destination
    # --------------------------------------------------------

    source_id = request.session.get(

        'source_station_id'

    )

    destination_id = request.session.get(

        'destination_station_id'

    )

    # --------------------------------------------------------
    # Get journey distance
    # --------------------------------------------------------

    journey_data = get_journey_distance(

        train=train,

        source_id=source_id,

        destination_id=destination_id

    )

    # --------------------------------------------------------
    # Get coach type
    # --------------------------------------------------------

    coach_type = (

        seat.coach.coach_type

    )

    # --------------------------------------------------------
    # Calculate final fare
    # --------------------------------------------------------

    fare_data = calculate_fare(

        distance=
            journey_data[
                'distance'
            ],

        stop_segments=
            journey_data[
                'stop_segments'
            ],

        coach_type=
            coach_type

    )

    # --------------------------------------------------------
    # Get passenger details from form
    #
    # These fields will be added to the HTML form
    # in the next step.
    # --------------------------------------------------------

    passenger_age = request.POST.get(

        'passenger_age'

    )

    passenger_gender = request.POST.get(

        'passenger_gender'

    )

    aadhaar_number = request.POST.get(

        'aadhaar_number'

    )

    # --------------------------------------------------------
    # Create main TicketBooking
    # --------------------------------------------------------

    booking = TicketBooking.objects.create(

        passenger=
            passenger,

        train=
            train,

        travel_date=
            travel_date,

        fare=
            fare_data[
                'total_fare'
            ],

        status=
            'PENDING'

    )

    # --------------------------------------------------------
    # Create BookingPassenger
    # --------------------------------------------------------

    BookingPassenger.objects.create(

        booking=
            booking,

        full_name=
            passenger.full_name,

        age=
            passenger_age
            if passenger_age
            else 0,

        gender=
            passenger_gender
            if passenger_gender
            else 'OTHER',

        aadhaar_number=
            aadhaar_number
            if aadhaar_number
            else '',

        seat=
            seat,

        fare=
            fare_data[
                'total_fare'
            ]

    )

    # --------------------------------------------------------
    # Go to payment
    # --------------------------------------------------------

    return redirect(

        'payment',

        booking_id=
            booking.id

    )


# ============================================================
# PAYMENT
# ============================================================

def payment(
    request,
    booking_id
):

    booking = get_object_or_404(

        TicketBooking,

        id=booking_id

    )

    return render(

        request,

        'ticket_booking/payment.html',

        {

            'booking':
                booking,

        }

    )