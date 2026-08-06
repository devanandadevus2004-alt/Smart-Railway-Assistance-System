from .seat_allocation_algorithm import (
    allocate_seats_for_passengers
)
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
    SeatReservation,

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
# CHECK GROUP VS PREFERENCE CONFLICT
# ============================================================

def check_group_preference_conflict(allocated_seats):

    lower_requested = []

    lower_not_allocated = []

    for allocation in allocated_seats:

        passenger = allocation.get("passenger", {})

        preference = (
            passenger.get(
                "berth_preference",
                ""
            )
            .strip()
            .lower()
        )

        seat_type = (
            allocation.get(
                "seat_type",
                ""
            )
            .strip()
            .lower()
        )

        if preference == "lower berth":

            lower_requested.append(
                passenger.get("full_name")
            )

            if "lower" not in seat_type:

                lower_not_allocated.append(
                    passenger.get("full_name")
                )

    if lower_not_allocated:

        return {

            "conflict": True,

            "requested": lower_requested,

            "not_allocated": lower_not_allocated,

        }

    return {

        "conflict": False

    }

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
def passenger_details(request, train_id):

    # --------------------------------------------------------
    # GET SELECTED TRAIN
    # --------------------------------------------------------

    train = get_object_or_404(
        Train,
        id=train_id
    )

    # --------------------------------------------------------
    # GET JOURNEY DETAILS FROM SESSION
    # --------------------------------------------------------

    source_id = request.session.get('source_station_id')
    destination_id = request.session.get('destination_station_id')
    travel_date = request.session.get('travel_date')
    passenger_count = request.session.get('passenger_count')

    # --------------------------------------------------------
    # VALIDATE SOURCE AND DESTINATION
    # --------------------------------------------------------

    if not source_id or not destination_id:
        return redirect('ticket_booking')

    # --------------------------------------------------------
    # VALIDATE PASSENGER COUNT
    # --------------------------------------------------------

    if not passenger_count:
        return redirect(
            'passenger_requirements',
            train_id=train.id
        )

    # Convert passenger_count to integer
    passenger_count = int(passenger_count)

    # --------------------------------------------------------
    # GET STATIONS
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
    # COMMON CONTEXT
    # --------------------------------------------------------

    context = {
        'train': train,
        'source_station': source_station,
        'destination_station': destination_station,
        'travel_date': travel_date,
        'passenger_count': passenger_count,
        'passenger_range': range(passenger_count),
    }

    # ========================================================
    # PROCESS PASSENGER DETAILS
    # ========================================================

    if request.method == 'POST':

        passengers = []

        for i in range(passenger_count):

            full_name = request.POST.get(f'full_name_{i}')
            age = request.POST.get(f'age_{i}')
            gender = request.POST.get(f'gender_{i}')
            aadhaar_number = request.POST.get(f'aadhaar_number_{i}')
            berth_preference = request.POST.get(f'berth_preference_{i}')
            priority = request.POST.get(
                f'priority_{i}',
                'normal'
            ).strip().lower()

            # ------------------------------------------------
            # VALIDATE REQUIRED FIELDS
            # ------------------------------------------------

            if not full_name or not age or not gender:

                context['error'] = (
                    f'Please complete the details for Passenger {i + 1}.'
                )

                return render(
                    request,
                    'ticket_booking/passenger_details.html',
                    context
                )

            # ------------------------------------------------
            # VALIDATE AGE
            # ------------------------------------------------

            try:
                age = int(age)

            except (TypeError, ValueError):

                context['error'] = (
                    f'Invalid age for Passenger {i + 1}.'
                )

                return render(
                    request,
                    'ticket_booking/passenger_details.html',
                    context
                )

            # ------------------------------------------------
            # SENIOR CITIZEN CHECK
            # ------------------------------------------------

            is_senior = age >= 60

            if is_senior:
                priority = 'senior_citizen'

            # ------------------------------------------------
            # STORE PASSENGER
            # ------------------------------------------------

            passengers.append({

                'full_name': full_name.strip(),
                'age': age,
                'gender': gender,
                'aadhaar_number': aadhaar_number or '',
                'berth_preference': berth_preference or '',
                'priority': priority,
                'is_senior': is_senior,
                'is_lactating_mother': priority == 'lactating_mother',
                'is_pregnant': priority == 'pregnant_woman',
                'is_disabled': priority == 'person_with_disability',
                'requires_priority_seat': priority != 'normal',

            })


        
        # ----------------------------------------------------
        # STORE PASSENGERS IN SESSION
        # ----------------------------------------------------

        request.session['passengers'] = passengers

        return redirect(
            'seat_recommendation',
            train_id=train.id
        )

    # ========================================================
    # DISPLAY PAGE
    # ========================================================

    return render(
        request,
        'ticket_booking/passenger_details.html',
        context
    )



def check_group_preference_conflict(allocated_seats):

    requested_lower = 0
    allocated_lower = 0

    for allocation in allocated_seats:

        passenger = allocation.get("passenger", {})

        requested = str(
            passenger.get(
                "berth_preference",
                ""
            )
        ).strip().upper()

        allocated = str(
            allocation.get(
                "seat_type",
                ""
            )
        ).strip().upper()

        if requested == "LOWER":

            requested_lower += 1


            if "LOWER" in allocated:

                allocated_lower += 1

    return {

        "conflict": requested_lower > allocated_lower,

        "requested_lower": requested_lower,

        "allocated_lower": allocated_lower

    }



def seat_recommendation(
    request,
    train_id
):


   
    # ========================================================
    # GET SELECTED TRAIN
    # ========================================================

    train = get_object_or_404(

        Train,

        id=train_id

    )


    # ========================================================
    # GET JOURNEY DETAILS FROM SESSION
    # ========================================================

    source_id = request.session.get(

        'source_station_id'

    )

    destination_id = request.session.get(

        'destination_station_id'

    )

    travel_date = request.session.get(

        'travel_date'

    )


    # ========================================================
    # GET SELECTED COACH TYPE
    # ========================================================

    selected_coach_type = request.session.get(

        'selected_coach_type'

    )


    # ========================================================
    # GET ALLOCATION MODE
    #
    # group -> Keep family together
    # lower -> Prioritize lower berths
    # ========================================================

    allocation_mode = request.session.get(

        "allocation_mode",

        "group"

    )


    # ========================================================
    # GET PASSENGER DETAILS
    # ========================================================

    passengers = request.session.get(

        'passengers'

    )


    


    # ========================================================
    # VALIDATE JOURNEY DETAILS
    # ========================================================

    if not source_id or not destination_id:

        return redirect(

            'ticket_booking'

        )


    # ========================================================
    # VALIDATE COACH TYPE
    # ========================================================

    if not selected_coach_type:

        return redirect(

            'passenger_requirements',

            train_id=train.id

        )



        


    # ========================================================
    # VALIDATE PASSENGER DETAILS
    # ========================================================

    if not passengers:

        return redirect(

            'passenger_requirements',

            train_id=train.id

        )


    # ========================================================
    # RELEASE EXPIRED SEAT LOCKS
    # ========================================================

    release_expired_seat_locks()
    # ========================================================
    # GET COACHES OF SELECTED COACH TYPE
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


    # ========================================================
    # CHECK WHETHER SELECTED COACH TYPE EXISTS
    # ========================================================

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
                    (
                        'The selected coach type is not available '
                        'for this train.'
                    )

            }

        )


    # ========================================================
    # FIND AVAILABLE SEATS
    # ========================================================

    available_seats = []


    for coach in coaches:


        for seat in coach.seats.all():


            # ------------------------------------------------
            # IGNORE INACTIVE SEATS
            # ------------------------------------------------

            if not seat.is_active:

                continue


            # ------------------------------------------------
            # CHECK WHETHER SEAT IS UNAVAILABLE
            # ------------------------------------------------

            if is_seat_unavailable(

                seat=seat,

                travel_date=travel_date,

                source_id=source_id,

                destination_id=destination_id

            ):

                continue


            # ------------------------------------------------
            # ADD AVAILABLE SEAT
            # ------------------------------------------------

            available_seats.append(

                {

                    'seat':
                        seat,

                    'coach':
                        coach,

                }

            )


    # ========================================================
    # CHECK WHETHER ENOUGH SEATS ARE AVAILABLE
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
                    (
                        'Sorry, enough seats are not available '
                        'in the selected coach type for all '
                        'passengers.'
                    )

            }

        )
     # ========================================================
    # CALL INTELLIGENT SEAT ALLOCATION ALGORITHM
    # ========================================================

    allocation_result = (

        allocate_seats_for_passengers(

            passengers=
                passengers,

            available_seats=
                available_seats,

            allocation_mode=
                allocation_mode

        )
    )


    


    # ========================================================
    # CHECK WHETHER ALLOCATION WAS SUCCESSFUL
    # ========================================================

    if not allocation_result.get(

        'success'

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
                    allocation_result.get(

                        'message',

                        'Unable to allocate suitable seats.'

                    ),

                'allocated_seats':
                    allocation_result.get(

                        'allocated_seats',

                        []

                    ),

            }

        )
            # ========================================================
    # GET SUCCESSFULLY ALLOCATED SEATS
    # ========================================================

    allocated_seats = (

        allocation_result.get(

            'allocated_seats',

            []

        )

    )


    # ========================================================
    # CHECK WHETHER USER PREFERENCES CONFLICT
    #
    # Example:
    # 5 passengers requested LOWER
    # but only 4 LOWER berths available.
    # ========================================================

    conflict = check_group_preference_conflict(

        allocated_seats

    )


    if conflict["conflict"]:


        # ----------------------------------------------------
        # Store temporary allocation
        # ----------------------------------------------------

        request.session["allocated_seats"] = allocated_seats


        # ----------------------------------------------------
        # Store conflict information
        # ----------------------------------------------------

        request.session["conflict"] = conflict


        # ----------------------------------------------------
        # Store selected train
        # ----------------------------------------------------

        request.session["selected_train_id"] = train.id


        # ----------------------------------------------------
        # Store coach type
        # ----------------------------------------------------

        request.session["selected_coach_type"] = (

            selected_coach_type

        )


        # ----------------------------------------------------
        # Show conflict page
        # ----------------------------------------------------

        return redirect(

            "seat_conflict"

        )
            # ========================================================
    # ADD EVALUATION INFORMATION
    #
    # This information is used by allocation_result.html.
    # ========================================================

    for allocation in allocated_seats:


        passenger = allocation.get(

            'passenger',

            {}

        )


        # ----------------------------------------------------
        # GET REQUESTED BERTH PREFERENCE
        # ----------------------------------------------------

        requested_berth = passenger.get(

            'berth_preference'

        )


        allocation[

            'berth_preference'

        ] = requested_berth


        # ----------------------------------------------------
        # CHECK BERTH PREFERENCE FULFILLED
        # ----------------------------------------------------

        if requested_berth:

            requested_berth_normalized = str(

                requested_berth

            ).strip().lower()


            actual_seat_type = str(

                allocation.get(

                    'seat_type',

                    ''

                )

            ).strip().lower()


            allocation[

                'berth_preference_fulfilled'

            ] = (

                requested_berth_normalized

                in

                actual_seat_type

            )

        else:

            allocation[

                'berth_preference_fulfilled'

            ] = False


        # ----------------------------------------------------
        # EXPLICIT SEAT PREFERENCE
        # ----------------------------------------------------

        preferred_seat_id = passenger.get(

            'preferred_seat_id'

        )


        allocation[

            'was_explicitly_selected'

        ] = bool(

            preferred_seat_id

        )


        # ----------------------------------------------------
        # CHECK EXPLICIT SEAT FULFILLED
        # ----------------------------------------------------

        if preferred_seat_id:

            try:

                allocation[

                    'explicit_seat_fulfilled'

                ] = (

                    int(

                        preferred_seat_id

                    )

                    ==

                    int(

                        allocation.get(

                            'seat_id'

                        )

                    )

                )

            except (

                TypeError,

                ValueError

            ):

                allocation[

                    'explicit_seat_fulfilled'

                ] = False

        else:

            allocation[

                'explicit_seat_fulfilled'

            ] = False

                # ----------------------------------------------------
        # CHECK COMFORT SEAT
        #
        # Lower and Side Lower are considered comfortable.
        # ----------------------------------------------------

        seat_type = str(

            allocation.get(

                'seat_type',

                ''

            )

        ).strip().lower()


        allocation[

            'comfort_seat_allocated'

        ] = (

            'lower berth'

            in

            seat_type

            or

            'side lower'

            in

            seat_type

        )


        # ----------------------------------------------------
        # GET PRIORITY
        # ----------------------------------------------------

        allocation[

            'priority'

        ] = passenger.get(

            'priority',

            'normal'

        )


        # ----------------------------------------------------
        # CHECK SAME COACH AS GROUP MEMBER
        # ----------------------------------------------------

        current_coach_id = allocation.get(

            'coach_id'

        )


        same_coach_count = 0


        for other_allocation in allocated_seats:

            if (

                other_allocation.get(

                    'coach_id'

                )

                ==

                current_coach_id

            ):

                same_coach_count += 1


        allocation[

            'same_coach_as_group'

        ] = (

            same_coach_count > 1

        )


        # ----------------------------------------------------
        # GROUP SUPPORT
        #
        # Check whether this passenger is sitting
        # near any priority passenger.
        # ----------------------------------------------------

        allocation[

            'near_priority_passenger'

        ] = False


        for other in allocated_seats:

            if other == allocation:

                continue


            other_priority = str(

                other.get(

                    'priority',

                    ''

                )

            ).lower()


            if other_priority in [

                'person with disability',

                'pregnant woman',

                'senior citizen',

                'medical',

                'lactating mother'

            ]:

                if (

                    allocation["coach_id"]

                    ==

                    other["coach_id"]

                    and

                    abs(

                        allocation["seat_number"]

                        -

                        other["seat_number"]

                    ) <= 2

                ):

                    allocation[

                        'near_priority_passenger'

                    ] = True

                    break
            # ========================================================
    # STORE ALLOCATION IN SESSION
    # ========================================================

    request.session[

        'allocated_seats'

    ] = allocated_seats


    # ========================================================
    # CLEAR TEMPORARY ALLOCATION MODE
    #
    # Prevent previous choice affecting future bookings
    # ========================================================

    request.session.pop(

        "allocation_mode",

        None

    )


    # ========================================================
    # STORE SELECTED TRAIN ID
    # ========================================================

    request.session[

        'selected_train_id'

    ] = train.id


    # ========================================================
    # STORE ALLOCATED COACH TYPE
    # ========================================================

    request.session[

        'allocated_coach_type'

    ] = selected_coach_type


    # ========================================================
    # GET SOURCE STATION
    # ========================================================

    source_station = get_object_or_404(

        Station,

        id=source_id

    )


    # ========================================================
    # GET DESTINATION STATION
    # ========================================================

    destination_station = get_object_or_404(

        Station,

        id=destination_id

    )


    print("Number of allocated passengers:", len(allocated_seats))
    for a in allocated_seats:
        print(a["passenger"])


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

            'source_station':
                source_station,

            'destination_station':
                destination_station,

            'travel_date':
                travel_date,

            'success':
                True,

            'allocation_mode':
                allocation_mode,

            'message':
                allocation_result.get(

                    'message',

                    (
                        'Seats successfully allocated '
                        'using the intelligent seat allocation '
                        'algorithm.'
                    )

                ),

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

# ============================================================
# CONFIRM BOOKING
#
# CURRENT VERSION
#
# Handles one passenger and one seat.
#
# UPDATED:
# - Creates TicketBooking
# - Creates BookingPassenger
# - Creates BOOKED SeatReservation
# - Stores travel date
# - Stores source station
# - Stores destination station
#
# This allows the intelligent seat allocation algorithm
# to check seat availability based on journey overlap.
# ============================================================

def confirm_booking(
    request
):




    print("========== CONFIRM BOOKING CALLED ==========")
    print("REQUEST METHOD:", request.method)
    print("POST DATA:", request.POST)
    print("SESSION DATA:", dict(request.session))
    # ========================================================
    # ONLY POST REQUESTS ARE ALLOWED
    # ========================================================

    if request.method != 'POST':

        return redirect(
            'ticket_booking'
        )


    # ========================================================
    # GET LOGGED-IN PASSENGER
    # ========================================================

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


    # ========================================================
    # GET BOOKING DETAILS
    # ========================================================

    train_id = request.POST.get(
        'train_id'
    )

    seat_id = request.POST.get(
        'seat_id'
    )

    travel_date = request.POST.get(
        'travel_date'
    )


    # ========================================================
    # GET TRAIN
    # ========================================================

    train = get_object_or_404(

        Train,

        id=train_id

    )


    # ========================================================
    # GET SELECTED SEAT
    # ========================================================

    seat = get_object_or_404(

        Seat,

        id=seat_id,

        coach__train=train

    )


    # ========================================================
    # GET SOURCE AND DESTINATION
    # ========================================================

    source_id = request.session.get(

        'source_station_id'

    )

    destination_id = request.session.get(

        'destination_station_id'

    )


    # ========================================================
    # VALIDATE JOURNEY DETAILS
    # ========================================================

    if not source_id or not destination_id:

        return redirect(

            'ticket_booking'

        )


    # ========================================================
    # CHECK WHETHER SELECTED SEAT IS STILL AVAILABLE
    #
    # This is important because the seat may have been
    # booked or locked by another passenger after the
    # seat selection page was opened.
    # ========================================================

    if is_seat_unavailable(

        seat=seat,

        travel_date=travel_date,

        source_id=source_id,

        destination_id=destination_id

    ):

        return render(

            request,

            'ticket_booking/allocation_result.html',

            {

                'train':
                    train,

                'success':
                    False,

                'message':
                    (
                        f'Seat {seat.seat_number} is no longer '
                        'available for the selected journey.'
                    )

            }

        )


    # ========================================================
    # GET JOURNEY DISTANCE
    # ========================================================

    journey_data = get_journey_distance(

        train=train,

        source_id=source_id,

        destination_id=destination_id

    )


    # ========================================================
    # GET COACH TYPE
    # ========================================================

    coach_type = (

        seat.coach.coach_type

    )


    # ========================================================
    # CALCULATE FARE
    # ========================================================

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


    # ========================================================
    # GET PASSENGER DETAILS
    # ========================================================

    passenger_age = request.POST.get(

        'passenger_age'

    )

    passenger_gender = request.POST.get(

        'passenger_gender'

    )

    aadhaar_number = request.POST.get(

        'aadhaar_number'

    )


    # ========================================================
    # CREATE BOOKING
    #
    # The booking is initially created as PENDING.
    # It will be associated with the payment process.
    # ========================================================

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


    # ========================================================
    # CREATE BOOKING PASSENGER
    # ========================================================

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


    # ========================================================
    # CREATE BOOKED SEAT RESERVATION
    #
    # IMPORTANT:
    #
    # This stores:
    #
    # 1. Seat
    # 2. Booking
    # 3. Travel date
    # 4. Source station
    # 5. Destination station
    # 6. BOOKED status
    #
    # The intelligent seat allocation algorithm later checks
    # this record to determine whether the seat can be reused
    # for another journey on the same train and date.
    # ========================================================

    SeatReservation.objects.create(

        seat=
            seat,

        booking=
            booking,

        travel_date=
            travel_date,

        source_station_id=
            source_id,

        destination_station_id=
            destination_id,

        status=
            'BOOKED'

    )


    # ========================================================
    # CONTINUE TO PAYMENT
    # ========================================================

    return redirect(

        'payment',

        booking_id=
            booking.id

    )


# ============================================================
# PAYMENT
# ============================================================

def payment(request, booking_id):

    booking = get_object_or_404(
        TicketBooking,
        id=booking_id
    )

    booking_passengers = BookingPassenger.objects.filter(
        booking=booking
    )

    return render(

        request,

        'ticket_booking/payment.html',

        {
            'booking': booking,
            'booking_passengers': booking_passengers,
        }

    )

# ============================================================
# MULTIPLE PASSENGER BOOKING SUMMARY
#
# Displays all passengers and their intelligently
# allocated seats before proceeding to payment.
# ============================================================

def multiple_booking_summary(
    request
):

    # --------------------------------------------------------
    # Get allocation data from session
    # --------------------------------------------------------

    allocated_seats = request.session.get(
        'allocated_seats'
    )

    # --------------------------------------------------------
    # Get selected train
    # --------------------------------------------------------

    train_id = request.session.get(
        'selected_train_id'
    )

    # --------------------------------------------------------
    # Validate allocation data
    # --------------------------------------------------------

    if not allocated_seats:

        return redirect(
            'ticket_booking'
        )

    # --------------------------------------------------------
    # If train ID is not stored in session,
    # try to get it from the first allocated seat.
    #
    # The allocation currently stores seat information,
    # so the train is better retrieved from the request URL
    # in the next update if necessary.
    # --------------------------------------------------------

    if not train_id:

        return redirect(
            'ticket_booking'
        )

    train = get_object_or_404(

        Train,

        id=train_id

    )

    # --------------------------------------------------------
    # Get journey details
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
    # Calculate journey distance
    # --------------------------------------------------------

    journey_data = get_journey_distance(

        train=train,

        source_id=source_id,

        destination_id=destination_id

    )

    # --------------------------------------------------------
    # Calculate fare for each passenger
    # --------------------------------------------------------

    total_fare = 0

    passenger_data = []

    for allocation in allocated_seats:

        coach_type = allocation.get(
            'coach_type'
        )

        # ----------------------------------------------------
        # Convert displayed coach type into fare-compatible
        # coach type where necessary.
        # ----------------------------------------------------

        if coach_type == 'Sleeper':

            fare_coach_type = 'SL'

        elif coach_type == 'AC 3 Tier':

            fare_coach_type = '3A'

        elif coach_type == 'AC 2 Tier':

            fare_coach_type = '2A'

        elif coach_type == 'First AC':

            fare_coach_type = '1A'

        else:

            fare_coach_type = 'GEN'

        # ----------------------------------------------------
        # Calculate passenger fare
        # ----------------------------------------------------

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
                fare_coach_type

        )

        passenger_fare = fare_data[
            'total_fare'
        ]

        total_fare += passenger_fare

        # ----------------------------------------------------
        # Create passenger summary data
        # ----------------------------------------------------

        passenger_data.append({

            'passenger':
                allocation.get(
                    'passenger'
                ),

            'seat_id':
                allocation.get(
                    'seat_id'
                ),

            'seat_number':
                allocation.get(
                    'seat_number'
                ),

            'seat_type':
                allocation.get(
                    'seat_type'
                ),

            'coach_number':
                allocation.get(
                    'coach_number'
                ),

            'coach_type':
                allocation.get(
                    'coach_type'
                ),

            'fare':
                passenger_fare,

        })

    # --------------------------------------------------------
    # Render multiple passenger booking summary
    # --------------------------------------------------------

    return render(

        request,

        'ticket_booking/multiple_booking_summary.html',

        {

            'train':
                train,

            'source_station':
                source_station,

            'destination_station':
                destination_station,

            'travel_date':
                travel_date,

            'passenger_data':
                passenger_data,

            'total_fare':
                total_fare,

            'distance':
                journey_data[
                    'distance'
                ],

            'distance_source':
                journey_data[
                    'distance_source'
                ],

        }

    )

# ============================================================
# CREATE MULTIPLE PASSENGER BOOKING
#
# Creates:
# 1. TicketBooking
# 2. BookingPassenger records
# 3. SeatReservation records with BOOKED status
#
# Stores journey-specific information:
# - Travel date
# - Source station
# - Destination station
#
# This allows the same seat to be reused for a non-overlapping
# journey on the same train and date.
# ============================================================

def create_multiple_booking(
    request
):

    # --------------------------------------------------------
    # Only POST request is allowed
    # --------------------------------------------------------

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
    # Get allocation information from session
    # --------------------------------------------------------

    allocated_seats = request.session.get(

        'allocated_seats'

    )


    # --------------------------------------------------------
    # Get selected train
    # --------------------------------------------------------

    train_id = request.session.get(

        'selected_train_id'

    )


    # --------------------------------------------------------
    # Get journey information
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
    # Validate required information
    # --------------------------------------------------------

    if not allocated_seats:

        return redirect(

            'ticket_booking'

        )


    if not train_id:

        return redirect(

            'ticket_booking'

        )


    if not source_id or not destination_id:

        return redirect(

            'ticket_booking'

        )


    if not travel_date:

        return redirect(

            'ticket_booking'

        )


    # --------------------------------------------------------
    # Get train
    # --------------------------------------------------------

    train = get_object_or_404(

        Train,

        id=train_id

    )


    # --------------------------------------------------------
    # Get source and destination stations
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
    # Calculate journey distance
    # --------------------------------------------------------

    journey_data = get_journey_distance(

        train=train,

        source_id=source_id,

        destination_id=destination_id

    )


    # ========================================================
    # FINAL AVAILABILITY CHECK
    #
    # Important:
    #
    # Seats were only recommended earlier.
    #
    # Before making them BOOKED, we check again because
    # another passenger may have booked the same seat
    # while this user was viewing the summary page.
    # ========================================================

    for allocation in allocated_seats:

        seat_id = allocation.get(

            'seat_id'

        )


        if not seat_id:

            return render(

                request,

                'ticket_booking/allocation_result.html',

                {

                    'train':
                        train,

                    'success':
                        False,

                    'message':
                        (
                            'Invalid seat information found '
                            'in the allocation.'
                        )

                }

            )


        seat = get_object_or_404(

            Seat,

            id=seat_id

        )


        if is_seat_unavailable(

            seat=seat,

            travel_date=travel_date,

            source_id=source_id,

            destination_id=destination_id

        ):

            return render(

                request,

                'ticket_booking/allocation_result.html',

                {

                    'train':
                        train,

                    'success':
                        False,

                    'message':
                        (
                            f'Seat {seat.seat_number} is no '
                            'longer available for this journey. '
                            'Please start the booking again.'
                        )

                }

            )


    # ========================================================
    # CALCULATE TOTAL FARE
    # ========================================================

    total_fare = 0


    passenger_fare_data = []


    for allocation in allocated_seats:


        coach_type = allocation.get(

            'coach_type'

        )


        # ----------------------------------------------------
        # Convert displayed coach type to fare code
        # ----------------------------------------------------

        if coach_type == 'Sleeper':

            fare_coach_type = 'SL'

        elif coach_type == 'AC 3 Tier':

            fare_coach_type = '3A'

        elif coach_type == 'AC 2 Tier':

            fare_coach_type = '2A'

        elif coach_type == 'First AC':

            fare_coach_type = '1A'

        else:

            fare_coach_type = 'GEN'


        # ----------------------------------------------------
        # Calculate fare
        # ----------------------------------------------------

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
                fare_coach_type

        )


        passenger_fare = fare_data[

            'total_fare'

        ]


        total_fare += passenger_fare


        passenger_fare_data.append({

            'allocation':
                allocation,

            'fare':
                passenger_fare,

        })


    # ========================================================
    # CREATE BOOKING
    # ========================================================

    with transaction.atomic():


        # ----------------------------------------------------
        # Create main ticket booking
        # ----------------------------------------------------

        booking = TicketBooking.objects.create(

            passenger=
                passenger,

            train=
                train,

            travel_date=
                travel_date,

            fare=
                total_fare,

            status=
                'PENDING'

        )


        # ====================================================
        # CREATE PASSENGER AND SEAT RESERVATION RECORDS
        # ====================================================

        for item in passenger_fare_data:


            allocation = item[

                'allocation'

            ]


            passenger_data = allocation.get(

                'passenger',

                {}

            )


            passenger_seat_id = allocation.get(

                'seat_id'

            )


            seat = get_object_or_404(

                Seat,

                id=passenger_seat_id

            )


            passenger_fare = item[

                'fare'

            ]


            # ------------------------------------------------
            # Create passenger booking record
            # ------------------------------------------------

            booking_passenger = (

                BookingPassenger.objects.create(

                    booking=
                        booking,

                    full_name=
                        passenger_data.get(
                            'full_name',
                            ''
                        ),

                    age=
                        passenger_data.get(
                            'age',
                            0
                        ),

                    gender=
                        passenger_data.get(
                            'gender',
                            'OTHER'
                        ),

                    aadhaar_number=
                        passenger_data.get(
                            'aadhaar_number',
                            ''
                        ),

                    seat=
                        seat,

                    fare=
                        passenger_fare

                )

            )


            # ------------------------------------------------
            # Create BOOKED seat reservation
            #
            # This stores the exact journey segment:
            #
            # Travel date
            # Source
            # Destination
            #
            # Therefore, availability can be checked based
            # on overlapping journeys.
            # ------------------------------------------------

            SeatReservation.objects.create(

                seat=
                    seat,

                booking=
                    booking,

                travel_date=
                    travel_date,

                source_station=
                    source_station,

                destination_station=
                    destination_station,

                status=
                    'BOOKED'

            )


    # ========================================================
    # CLEAR OLD ALLOCATION SESSION DATA
    #
    # This prevents the same allocation from being reused
    # accidentally after booking.
    # ========================================================

    request.session.pop(

        'allocated_seats',

        None

    )

    request.session.pop(

        'selected_train_id',

        None

    )

    request.session.pop(

        'allocated_coach_type',

        None

    )


    # ========================================================
    # REDIRECT TO PAYMENT
    # ========================================================

    return redirect(

        'payment',

        booking_id=
            booking.id

    )



# ============================================================
# SEAT CONFLICT
# ============================================================

def seat_conflict(request):

    conflict = request.session.get(
        "conflict"
    )

    if not conflict:

        return redirect(
            "ticket_booking"
        )

    return render(

        request,

        "ticket_booking/seat_conflict.html",

        {

            "conflict": conflict

        }

    )

# ============================================================
# SAVE USER DECISION
# ============================================================

def save_allocation_strategy(request):

    if request.method != "POST":

        return redirect(
            "ticket_booking"
        )

    strategy = request.POST.get(
        "strategy"
    )

    request.session[
        "allocation_strategy"
    ] = strategy

    return redirect(
        "multiple_booking_summary"
    )


def continue_group_booking(request):

    allocated_seats = request.session.get(
        "allocated_seats"
    )

    if not allocated_seats:

        return redirect(
            "ticket_booking"
        )

    return redirect(
        "allocation_result"
    )


def allocation_result(request):

    allocated_seats = request.session.get(
        "allocated_seats"
    )

    if not allocated_seats:

        return redirect(
            "ticket_booking"
        )

    train = get_object_or_404(
        Train,
        id=request.session["selected_train_id"]
    )

    source_station = get_object_or_404(
        Station,
        id=request.session["source_station_id"]
    )

    destination_station = get_object_or_404(
        Station,
        id=request.session["destination_station_id"]
    )

    return render(

        request,

        "ticket_booking/allocation_result.html",

        {

            "train": train,

            "allocated_seats": allocated_seats,

            "selected_coach_type":
                request.session.get(
                    "allocated_coach_type"
                ),

            "source_station":
                source_station,

            "destination_station":
                destination_station,

            "travel_date":
                request.session.get(
                    "travel_date"
                ),

            "success": True,

            "message":
                "Seats allocated successfully."

        }

    )

def assign_companion_seats(
    allocated_seats,
    remaining_passengers,
    available_seats
):
    """
    Allocate nearby seats for companions of
    priority passengers.
    """

    return allocated_seats


def keep_group_together(request):

    request.session["allocation_mode"] = "group"

    return redirect(
        "allocate_seats",
        train_id=request.session["selected_train_id"]
    )


def prioritize_lower_berths(request):

    request.session["allocation_mode"] = "lower"

    return redirect(
        "allocate_seats",
        train_id=request.session["selected_train_id"]
    )

def process_payment(request, booking_id):

    if request.method == "POST":

        booking = get_object_or_404(
            TicketBooking,
            id=booking_id
        )

        payment_method = request.POST.get(
            "payment_method"
        )

        # temporary payment success simulation

        booking.status = "CONFIRMED"
        booking.save()

        return render(
            request,
            "ticket_booking/payment_success.html",
            {
                "booking": booking,
                "payment_method": payment_method
            }
        )