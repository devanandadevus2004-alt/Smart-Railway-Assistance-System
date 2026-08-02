import json
from datetime import timedelta

from django.utils import timezone
from django.db import transaction

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

    distance_record = (
        TrainStopDistance.objects.filter(
            train=train,
            source_station_id=source_id,
            destination_station_id=destination_id
        ).first()
    )

    if distance_record:

        return {
            "distance": distance_record.distance,
            "distance_source": "Actual",
            "stop_segments": None
        }

    source_stop = (
        TrainStop.objects.filter(
            train=train,
            station_id=source_id
        ).first()
    )

    destination_stop = (
        TrainStop.objects.filter(
            train=train,
            station_id=destination_id
        ).first()
    )

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
        "distance": None,
        "distance_source": "Estimated",
        "stop_segments": stop_segments
    }


# ============================================================
# SEAT LOCK SETTINGS
# ============================================================

SEAT_LOCK_MINUTES = 10


# ============================================================
# RELEASE EXPIRED SEAT LOCKS
# ============================================================

def release_expired_seat_locks():

    now = timezone.now()

    SeatReservation.objects.filter(
        status='LOCKED',
        lock_expires_at__lte=now
    ).update(
        status='EXPIRED'
    )


# ============================================================
# CHECK WHETHER TWO JOURNEYS OVERLAP
# ============================================================

def journeys_overlap(
    reservation,
    source_id,
    destination_id
):

    train_id = reservation.seat.coach.train_id

    reservation_source_order = (
        TrainStop.objects.filter(
            train_id=train_id,
            station_id=reservation.source_station_id
        )
        .values_list(
            'stop_order',
            flat=True
        )
        .first()
    )

    reservation_destination_order = (
        TrainStop.objects.filter(
            train_id=train_id,
            station_id=reservation.destination_station_id
        )
        .values_list(
            'stop_order',
            flat=True
        )
        .first()
    )

    current_source_order = (
        TrainStop.objects.filter(
            train_id=train_id,
            station_id=source_id
        )
        .values_list(
            'stop_order',
            flat=True
        )
        .first()
    )

    current_destination_order = (
        TrainStop.objects.filter(
            train_id=train_id,
            station_id=destination_id
        )
        .values_list(
            'stop_order',
            flat=True
        )
        .first()
    )

    if None in [
        reservation_source_order,
        reservation_destination_order,
        current_source_order,
        current_destination_order
    ]:

        return False

    if current_destination_order <= reservation_source_order:

        return False

    if reservation_destination_order <= current_source_order:

        return False

    return True


# ============================================================
# CHECK IF SEAT IS CURRENTLY UNAVAILABLE
# ============================================================

def is_seat_unavailable(
    seat,
    travel_date,
    source_id,
    destination_id
):

    release_expired_seat_locks()

    reservations = (
        SeatReservation.objects.filter(
            seat=seat,
            travel_date=travel_date,
            status__in=[
                'LOCKED',
                'BOOKED'
            ]
        )
    )

    for reservation in reservations:

        if journeys_overlap(
            reservation,
            source_id,
            destination_id
        ):

            return True

    return False


# ============================================================
# LOCK MULTIPLE SEATS
# ============================================================

def lock_seats(
    train,
    seat_ids,
    travel_date,
    source_id,
    destination_id
):

    release_expired_seat_locks()

    now = timezone.now()

    lock_expires_at = (
        now +
        timedelta(
            minutes=SEAT_LOCK_MINUTES
        )
    )

    with transaction.atomic():

        seats = (
            Seat.objects
            .select_for_update()
            .filter(
                id__in=seat_ids,
                coach__train=train
            )
        )

        if seats.count() != len(
            set(seat_ids)
        ):

            return {
                'success': False,
                'message':
                    'One or more selected seats are invalid.'
            }

        for seat in seats:

            if is_seat_unavailable(
                seat=seat,
                travel_date=travel_date,
                source_id=source_id,
                destination_id=destination_id
            ):

                return {
                    'success': False,
                    'message':
                        f'Seat {seat.seat_number} '
                        f'is no longer available.'
                }

        reservations = []

        for seat in seats:

            reservation = (
                SeatReservation.objects.create(

                    seat=seat,

                    travel_date=travel_date,

                    source_station_id=source_id,

                    destination_station_id=destination_id,

                    status='LOCKED',

                    locked_at=now,

                    lock_expires_at=lock_expires_at

                )
            )

            reservations.append(
                reservation
            )

        return {
            'success': True,

            'reservations':
                reservations,

            'lock_expires_at':
                lock_expires_at
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

        request.session[
            'source_station_id'
        ] = source_id

        request.session[
            'destination_station_id'
        ] = destination_id

        request.session[
            'travel_date'
        ] = travel_date

        if source_id and destination_id:

            source_stops = (
                TrainStop.objects.filter(
                    station_id=source_id
                )
            )

            destination_stops = (
                TrainStop.objects.filter(
                    station_id=destination_id
                )
            )

            destination_orders = {}

            for stop in destination_stops:

                destination_orders[
                    stop.train_id
                ] = stop.stop_order

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
# PASSENGER REQUIREMENTS
# ============================================================

# ============================================================
# PASSENGER REQUIREMENTS
# ============================================================

def passenger_requirements(
    request,
    train_id
):

    # --------------------------------------------------------
    # Get selected train
    # --------------------------------------------------------

    train = get_object_or_404(
        Train,
        id=train_id
    )

    # --------------------------------------------------------
    # Get journey details from session
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
    # Check journey details
    # --------------------------------------------------------

    if not source_id or not destination_id:

        return redirect(
            'ticket_booking'
        )

    # --------------------------------------------------------
    # Get stations
    # --------------------------------------------------------

    source_station = get_object_or_404(
        Station,
        id=source_id
    )

    destination_station = get_object_or_404(
        Station,
        id=destination_id
    )

    # --------------------------------------------------------
    # Handle form submission
    # --------------------------------------------------------

    if request.method == 'POST':

        # ----------------------------------------------------
        # Get selected coach type
        # ----------------------------------------------------

        coach_type = request.POST.get(
            'coach_type'
        )

        # ----------------------------------------------------
        # Get passenger count
        # ----------------------------------------------------

        passenger_count = request.POST.get(
            'passenger_count'
        )

        # ----------------------------------------------------
        # Validate coach type
        # ----------------------------------------------------

        valid_coach_types = [
            'GEN',
            'SL',
            '3A',
            '2A',
            '1A'
        ]

        if coach_type not in valid_coach_types:

            return render(

                request,

                'ticket_booking/passenger_requirements.html',

                {
                    'train':
                        train,

                    'source_station':
                        source_station,

                    'destination_station':
                        destination_station,

                    'travel_date':
                        travel_date,

                    'error':
                        'Please select a valid coach type.'
                }

            )

        # ----------------------------------------------------
        # Convert passenger count to integer
        # ----------------------------------------------------

        try:

            passenger_count = int(
                passenger_count
            )

        except (
            TypeError,
            ValueError
        ):

            passenger_count = 0

        # ----------------------------------------------------
        # Validate passenger count
        # ----------------------------------------------------

        if passenger_count < 1:

            return render(

                request,

                'ticket_booking/passenger_requirements.html',

                {
                    'train':
                        train,

                    'source_station':
                        source_station,

                    'destination_station':
                        destination_station,

                    'travel_date':
                        travel_date,

                    'error':
                        'Please select at least one passenger.'
                }

            )

        # ----------------------------------------------------
        # Maximum 6 passengers
        # ----------------------------------------------------

        if passenger_count > 6:

            return render(

                request,

                'ticket_booking/passenger_requirements.html',

                {
                    'train':
                        train,

                    'source_station':
                        source_station,

                    'destination_station':
                        destination_station,

                    'travel_date':
                        travel_date,

                    'error':
                        'Maximum 6 passengers are allowed per booking.'
                }

            )

        # ----------------------------------------------------
        # Store selected coach type in session
        # ----------------------------------------------------

        request.session[
            'selected_coach_type'
        ] = coach_type

        # ----------------------------------------------------
        # Store passenger count in session
        # ----------------------------------------------------

        request.session[
            'passenger_count'
        ] = passenger_count

        # ----------------------------------------------------
        # Continue to passenger details
        # ----------------------------------------------------

        return redirect(

            'passenger_details',

            train_id=train.id

        )

    # --------------------------------------------------------
    # Display requirements page
    # --------------------------------------------------------

    return render(

        request,

        'ticket_booking/passenger_requirements.html',

        {
            'train':
                train,

            'source_station':
                source_station,

            'destination_station':
                destination_station,

            'travel_date':
                travel_date,
        }

    )

# ============================================================
# PASSENGER DETAILS AND PREFERENCES
# ============================================================

def passenger_details(
    request,
    train_id
):

    train = get_object_or_404(
        Train,
        id=train_id
    )

    source_id = request.session.get(
        'source_station_id'
    )

    destination_id = request.session.get(
        'destination_station_id'
    )

    travel_date = request.session.get(
        'travel_date'
    )

    passenger_count = request.session.get(
        'passenger_count'
    )

    if not source_id or not destination_id:

        return redirect(
            'ticket_booking'
        )

    if not passenger_count:

        return redirect(
            'passenger_requirements',
            train_id=train.id
        )

    source_station = get_object_or_404(
        Station,
        id=source_id
    )

    destination_station = get_object_or_404(
        Station,
        id=destination_id
    )

    if request.method == 'POST':

        passengers = []

        for i in range(
            passenger_count
        ):

            full_name = request.POST.get(
                f'full_name_{i}'
            )

            age = request.POST.get(
                f'age_{i}'
            )

            gender = request.POST.get(
                f'gender_{i}'
            )

            aadhaar_number = request.POST.get(
                f'aadhaar_number_{i}'
            )

            berth_preference = request.POST.get(
                f'berth_preference_{i}'
            )

            if not full_name or not age or not gender:

                return render(

                    request,

                    'ticket_booking/passenger_details.html',

                    {
                        'train':
                            train,

                        'source_station':
                            source_station,

                        'destination_station':
                            destination_station,

                        'travel_date':
                            travel_date,

                        'passenger_count':
                            passenger_count,

                        'error':
                            f'Please complete the details for Passenger {i + 1}.'
                    }

                )

            try:

                age = int(
                    age
                )

            except (
                TypeError,
                ValueError
            ):

                return render(

                    request,

                    'ticket_booking/passenger_details.html',

                    {
                        'train':
                            train,

                        'source_station':
                            source_station,

                        'destination_station':
                            destination_station,

                        'travel_date':
                            travel_date,

                        'passenger_count':
                            passenger_count,

                        'error':
                            f'Invalid age for Passenger {i + 1}.'
                    }

                )

            is_senior = age >= 60

            passengers.append({

                'full_name':
                    full_name,

                'age':
                    age,

                'gender':
                    gender,

                'aadhaar_number':
                    aadhaar_number or '',

                'berth_preference':
                    berth_preference or '',

                'is_senior':
                    is_senior,

            })

        request.session[
            'passengers'
        ] = passengers

        # ----------------------------------------------------
        # IMPORTANT:
        # URL configuration contains seat_recommendation.
        # Therefore redirect to seat_recommendation.
        # ----------------------------------------------------

        return redirect(

            'seat_recommendation',

            train_id=train.id

        )

    return render(

        request,

        'ticket_booking/passenger_details.html',

        {
            'train':
                train,

            'source_station':
                source_station,

            'destination_station':
                destination_station,

            'travel_date':
                travel_date,

            'passenger_count':
                passenger_count,

        }

    )


# ============================================================
# SEAT RECOMMENDATION
#
# Passenger selects coach type first.
#
# GEN:
#   - General coach only
#   - Preferred berth selection disabled
#
# SL / 3A / 2A / 1A:
#   - Only selected coach type is considered
#   - Berth preference is used by the algorithm
# ============================================================

def seat_recommendation(
    request,
    train_id
):

    # --------------------------------------------------------
    # Get selected train
    # --------------------------------------------------------

    train = get_object_or_404(
        Train,
        id=train_id
    )

    # --------------------------------------------------------
    # Get journey details from session
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
    # Get selected coach type
    #
    # This was selected by the passenger on the
    # Passenger Requirements page.
    # --------------------------------------------------------

    selected_coach_type = request.session.get(
        'selected_coach_type'
    )

    # --------------------------------------------------------
    # Get passenger details
    # --------------------------------------------------------

    passengers = request.session.get(
        'passengers'
    )

    # --------------------------------------------------------
    # Validate journey details
    # --------------------------------------------------------

    if not source_id or not destination_id:

        return redirect(
            'ticket_booking'
        )

    # --------------------------------------------------------
    # Validate coach type
    # --------------------------------------------------------

    if not selected_coach_type:

        return redirect(

            'passenger_requirements',

            train_id=train.id

        )

    # --------------------------------------------------------
    # Validate passenger details
    # --------------------------------------------------------

    if not passengers:

        return redirect(

            'passenger_requirements',

            train_id=train.id

        )

    # --------------------------------------------------------
    # Release expired seat locks
    # --------------------------------------------------------

    release_expired_seat_locks()

    # ========================================================
    # GET COACHES
    #
    # IMPORTANT:
    # Only coaches belonging to the passenger-selected
    # coach type will be considered.
    # ========================================================

    coaches = (

        Coach.objects

        .filter(

            train=train,

            coach_type=selected_coach_type,

            is_bookable=True

        )

        .prefetch_related(
            'seats'
        )

        .order_by(
            'id'
        )

    )

    # --------------------------------------------------------
    # Check whether selected coach type exists
    # --------------------------------------------------------

    if not coaches.exists():

        return render(

            request,

            'ticket_booking/allocation_result.html',

            {

                'train':
                    train,

                'success':
                    False,

                'selected_coach_type':
                    selected_coach_type,

                'message':
                    'The selected coach type is not available '
                    'for this train.'

            }

        )

    # ========================================================
    # FIND AVAILABLE SEATS
    # ========================================================

    available_seats = []

    for coach in coaches:

        for seat in coach.seats.all():

            # ------------------------------------------------
            # Ignore inactive seats
            # ------------------------------------------------

            if not seat.is_active:

                continue

            # ------------------------------------------------
            # Check whether seat is unavailable for the
            # selected journey
            # ------------------------------------------------

            if is_seat_unavailable(

                seat=seat,

                travel_date=travel_date,

                source_id=source_id,

                destination_id=destination_id

            ):

                continue

            # ------------------------------------------------
            # Add available seat
            # ------------------------------------------------

            available_seats.append({

                'seat':
                    seat,

                'coach':
                    coach,

            })

    # ========================================================
    # CHECK SEAT AVAILABILITY
    # ========================================================

    if len(
        available_seats
    ) < len(
        passengers
    ):

        return render(

            request,

            'ticket_booking/allocation_result.html',

            {

                'train':
                    train,

                'success':
                    False,

                'selected_coach_type':
                    selected_coach_type,

                'message':
                    'Sorry, enough seats are not available '
                    'in the selected coach type for all passengers.'

            }

        )

    # ========================================================
    # CREATE WORKING COPY
    # ========================================================

    remaining_seats = list(
        available_seats
    )

    allocated_seats = []

    # ========================================================
    # ALLOCATE SEATS FOR EACH PASSENGER
    # ========================================================

    for passenger in passengers:

        preferred_seat = None

        # ----------------------------------------------------
        # GENERAL COACH
        #
        # Preferred berth selection is disabled for GEN.
        # Therefore, the algorithm simply selects the first
        # available seat.
        # ----------------------------------------------------

        if selected_coach_type == 'GEN':

            preferred_seat = (
                remaining_seats[0]
            )

        # ----------------------------------------------------
        # RESERVED COACHES
        #
        # SL / 3A / 2A / 1A
        #
        # Try to satisfy passenger's berth preference.
        # ----------------------------------------------------

        else:

            berth_preference = (

                passenger.get(
                    'berth_preference'
                )

            )

            # ------------------------------------------------
            # Try to find preferred berth
            # ------------------------------------------------

            if berth_preference:

                for item in remaining_seats:

                    seat = item[
                        'seat'
                    ]

                    seat_type = (

                        seat.get_seat_type_display()

                    )

                    if (

                        berth_preference.lower()

                        in

                        seat_type.lower()

                    ):

                        preferred_seat = item

                        break

            # ------------------------------------------------
            # If preferred berth is unavailable,
            # use first available seat.
            # ------------------------------------------------

            if preferred_seat is None:

                preferred_seat = (

                    remaining_seats[0]

                )

        # ====================================================
        # REMOVE SELECTED SEAT FROM WORKING LIST
        # ====================================================

        remaining_seats.remove(

            preferred_seat

        )

        # ----------------------------------------------------
        # Get selected seat
        # ----------------------------------------------------

        selected_seat = (

            preferred_seat[
                'seat'
            ]

        )

        # ----------------------------------------------------
        # Get selected coach
        # ----------------------------------------------------

        selected_coach = (

            preferred_seat[
                'coach'
            ]

        )

        # ====================================================
        # STORE ALLOCATION
        # ====================================================

        allocated_seats.append({

            'passenger':
                passenger,

            'seat_id':
                selected_seat.id,

            'seat_number':
                selected_seat.seat_number,

            'seat_type':
                selected_seat.get_seat_type_display(),

            'coach_number':
                selected_coach.coach_number,

            'coach_type':
                selected_coach.get_coach_type_display(),

        })

    # ========================================================
    # STORE ALLOCATION IN SESSION
    # ========================================================

    request.session[
        'allocated_seats'
    ] = allocated_seats

    # --------------------------------------------------------
    # Store selected coach type as well
    # --------------------------------------------------------

    request.session[
        'allocated_coach_type'
    ] = selected_coach_type

    # ========================================================
    # DISPLAY ALLOCATION RESULT
    # ========================================================

    return render(

        request,

        'ticket_booking/allocation_result.html',

        {

            'train':
                train,

            'allocated_seats':
                allocated_seats,

            'selected_coach_type':
                selected_coach_type,

            'success':
                True,

        }

    )


# ============================================================
# ALLOCATE SEATS
#
# COMPATIBILITY FUNCTION
#
# Kept so any old URL or code referring to allocate_seats
# will continue to work.
# ============================================================

def allocate_seats(
    request,
    train_id
):

    return seat_recommendation(

        request,

        train_id

    )


# ============================================================
# SELECT SEAT
#
# CURRENT MANUAL SEAT LAYOUT PAGE
# ============================================================

def select_seat(
    request,
    train_id
):

    train = get_object_or_404(
        Train,
        id=train_id
    )

    source_id = request.session.get(
        'source_station_id'
    )

    destination_id = request.session.get(
        'destination_station_id'
    )

    travel_date = request.session.get(
        'travel_date'
    )

    travel_date = request.GET.get(
        'travel_date',
        travel_date
    )

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

    coaches_data = []

    for coach in coaches:

        seats_data = []

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
#
# CURRENT VERSION
#
# Handles one manually selected seat.
# ============================================================

def booking_summary(
    request
):

    train_id = request.GET.get(
        'train_id'
    )

    seat_id = request.GET.get(
        'seat_id'
    )

    travel_date = request.GET.get(
        'travel_date'
    )

    passenger_id = (
        request.session.get(
            'passenger_id'
        )
    )

    if not passenger_id:

        return redirect(
            'login'
        )

    train = get_object_or_404(

        Train,

        id=train_id

    )

    seat = get_object_or_404(

        Seat,

        id=seat_id

    )

    passenger = get_object_or_404(

        Passenger,

        id=passenger_id

    )

    source_id = request.session.get(

        'source_station_id'

    )

    destination_id = request.session.get(

        'destination_station_id'

    )

    journey_data = get_journey_distance(

        train=train,

        source_id=source_id,

        destination_id=destination_id

    )

    coach_type = (

        seat.coach.coach_type

    )

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

    source_station = get_object_or_404(

        Station,

        id=source_id

    )

    destination_station = get_object_or_404(

        Station,

        id=destination_id

    )

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
#
# CURRENT VERSION
#
# Handles one passenger and one seat.
# ============================================================

def confirm_booking(
    request
):

    if request.method != 'POST':

        return redirect(
            'ticket_booking'
        )

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

    train_id = request.POST.get(
        'train_id'
    )

    seat_id = request.POST.get(
        'seat_id'
    )

    travel_date = request.POST.get(
        'travel_date'
    )

    train = get_object_or_404(

        Train,

        id=train_id

    )

    seat = get_object_or_404(

        Seat,

        id=seat_id

    )

    source_id = request.session.get(

        'source_station_id'

    )

    destination_id = request.session.get(

        'destination_station_id'

    )

    journey_data = get_journey_distance(

        train=train,

        source_id=source_id,

        destination_id=destination_id

    )

    coach_type = (

        seat.coach.coach_type

    )

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

    passenger_age = request.POST.get(

        'passenger_age'

    )

    passenger_gender = request.POST.get(

        'passenger_gender'

    )

    aadhaar_number = request.POST.get(

        'aadhaar_number'

    )

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