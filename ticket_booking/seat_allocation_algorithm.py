# ============================================================
# SMART SEAT ALLOCATION ALGORITHM
# File:
# ticket_booking/seat_allocation_algorithm.py
# ============================================================


# ============================================================
# NORMALIZE TEXT
# ============================================================

def normalize_text(value):

    if value is None:
        return ''

    return str(value).strip().lower().replace('_', ' ')


# ============================================================
# GET PASSENGER PRIORITY
# ============================================================

def get_passenger_priority(passenger):

    priority = normalize_text(
        passenger.get(
            'priority',
            'none'
        )
    )

    # --------------------------------------------------------
    # AUTOMATIC SENIOR CITIZEN PRIORITY
    # --------------------------------------------------------

    if passenger.get(
        'is_senior',
        False
    ):

        return 'senior citizen'

    # --------------------------------------------------------
    # NORMALIZE PRIORITY VALUES FROM FORM
    # --------------------------------------------------------

    priority_mapping = {

        'none':
            'normal',

        'normal':
            'normal',

        'pregnant':
            'pregnant woman',

        'pregnant woman':
            'pregnant woman',

        'lactating':
            'lactating mother',

        'lactating mother':
            'lactating mother',

        'disability':
            'person with disability',

        'person with disability':
            'person with disability',

        'medical':
            'medical',

        'medical accessibility requirement':
            'medical',

    }

    return priority_mapping.get(

        priority,

        'normal'

    )


# ============================================================
# GET DISPLAY PRIORITY
# ============================================================

def get_priority_display(
    passenger
):

    priority = get_passenger_priority(

        passenger

    )

    priority_names = {

        'normal':
            'Normal Passenger',

        'senior citizen':
            'Senior Citizen',

        'pregnant woman':
            'Pregnant Woman',

        'lactating mother':
            'Lactating Mother',

        'person with disability':
            'Person with Disability',

        'medical':
            'Medical / Accessibility Requirement',

    }

    return priority_names.get(

        priority,

        'Normal Passenger'

    )


# ============================================================
# CHECK COACH TYPE MATCH
# ============================================================

def coach_type_matches(
    passenger,
    coach
):

    preferred_coach_type = normalize_text(

        passenger.get(
            'coach_type'
        )

    )

    if not preferred_coach_type:

        return True

    actual_coach_type = normalize_text(

        coach.coach_type

    )

    return (

        preferred_coach_type
        ==
        actual_coach_type

    )


# ============================================================
# CHECK BERTH PREFERENCE
# ============================================================

def berth_matches(
    passenger,
    seat
):

    berth_preference = normalize_text(

        passenger.get(
            'berth_preference'
        )

    )

    if not berth_preference:

        return False

    seat_type = normalize_text(

        seat.get_seat_type_display()

    )

    # --------------------------------------------------------
    # NORMALIZE BERTH NAMES
    # --------------------------------------------------------

    berth_mapping = {

        'lower':
            'lower berth',

        'middle':
            'middle berth',

        'upper':
            'upper berth',

        'side lower':
            'side lower berth',

        'side upper':
            'side upper berth',

    }

    expected_seat_type = berth_mapping.get(

        berth_preference,

        berth_preference

    )

    return (

        expected_seat_type
        ==
        seat_type

    )


# ============================================================
# GET REQUESTED BERTH DISPLAY
# ============================================================

def get_requested_berth(
    passenger
):

    berth = normalize_text(

        passenger.get(
            'berth_preference'
        )

    )

    if not berth:

        return 'No specific preference'

    berth_names = {

        'lower':
            'Lower Berth',

        'middle':
            'Middle Berth',

        'upper':
            'Upper Berth',

        'side lower':
            'Side Lower Berth',

        'side upper':
            'Side Upper Berth',

    }

    return berth_names.get(

        berth,

        berth.title()

    )


# ============================================================
# CHECK EXPLICIT SEAT SELECTION
# ============================================================

def has_explicit_seat_preference(
    passenger
):

    return bool(

        passenger.get(
            'preferred_seat_id'
        )

    )


# ============================================================
# CHECK SAME COACH
# ============================================================

def is_same_coach(
    coach,
    allocated_seats
):

    for allocation in allocated_seats:

        if (

            allocation.get(
                'coach_id'
            )
            ==
            coach.id

        ):

            return True

    return False


# ============================================================
# CALCULATE SEAT DISTANCE
# ============================================================

def calculate_seat_distance(
    seat,
    coach,
    allocated_seats
):

    if not allocated_seats:

        return None

    try:

        current_seat_number = int(

            seat.seat_number

        )

    except (
        TypeError,
        ValueError
    ):

        return None

    distances = []

    for allocation in allocated_seats:

        if (

            allocation.get(
                'coach_id'
            )
            !=
            coach.id

        ):

            continue

        try:

            allocated_seat_number = int(

                allocation.get(
                    'seat_number'
                )

            )

            distance = abs(

                current_seat_number
                -
                allocated_seat_number

            )

            distances.append(

                distance

            )

        except (
            TypeError,
            ValueError
        ):

            continue

    if not distances:

        return None

    return min(

        distances

    )


# ============================================================
# CHECK COMFORT SEAT
# ============================================================

def is_comfort_seat(
    seat
):

    seat_type = normalize_text(

        seat.get_seat_type_display()

    )

    return (

        'side lower' in seat_type
        or
        seat_type == 'lower berth'

    )


# ============================================================
# CALCULATE SEAT SCORE
# ============================================================

def calculate_seat_score(
    passenger,
    seat,
    coach,
    allocated_seats
):

    score = 0

    reasons = []

    seat_type = normalize_text(

        seat.get_seat_type_display()

    )

    priority = get_passenger_priority(

        passenger

    )


    # ========================================================
    # 1. EXPLICIT SEAT PREFERENCE
    # ========================================================

    preferred_seat_id = passenger.get(

        'preferred_seat_id'

    )

    if preferred_seat_id:

        try:

            preferred_seat_id = int(

                preferred_seat_id

            )

        except (
            TypeError,
            ValueError
        ):

            preferred_seat_id = None


        if (

            preferred_seat_id
            ==
            seat.id

        ):

            score += 1000

            reasons.append(

                'Passenger selected this seat explicitly.'

            )


    # ========================================================
    # 2. PERSON WITH DISABILITY
    # ========================================================

    if priority == 'person with disability':

        if is_comfort_seat(

            seat

        ):

            score += 400

            reasons.append(

                'Comfortable berth prioritized '
                'for person with disability.'

            )

        if seat_type == 'lower berth':

            score += 200

            reasons.append(

                'Lower berth prioritized for easier access.'

            )


    # ========================================================
    # 3. PREGNANT WOMAN
    # ========================================================

    if priority == 'pregnant woman':

        if is_comfort_seat(

            seat

        ):

            score += 400

            reasons.append(

                'Comfortable berth prioritized '
                'for pregnant woman.'

            )

        if seat_type == 'lower berth':

            score += 200

            reasons.append(

                'Lower berth prioritized '
                'for pregnant woman.'

            )


    # ========================================================
    # 4. LACTATING MOTHER
    # ========================================================

    if priority == 'lactating mother':

        if is_comfort_seat(

            seat

        ):

            score += 350

            reasons.append(

                'Comfortable berth prioritized '
                'for lactating mother.'

            )

        if seat_type == 'lower berth':

            score += 150

            reasons.append(

                'Lower berth prioritized '
                'for lactating mother.'

            )


    # ========================================================
    # 5. SENIOR CITIZEN
    # ========================================================

    if priority == 'senior citizen':

        if is_comfort_seat(

            seat

        ):

            score += 300

            reasons.append(

                'Comfortable berth prioritized '
                'for senior citizen.'

            )

        if seat_type == 'lower berth':

            score += 150

            reasons.append(

                'Lower berth prioritized '
                'for senior citizen.'

            )


    # ========================================================
    # 6. MEDICAL / ACCESSIBILITY REQUIREMENT
    # ========================================================

    if priority == 'medical':

        if is_comfort_seat(

            seat

        ):

            score += 300

            reasons.append(

                'Comfortable berth prioritized '
                'for medical or accessibility requirement.'

            )

        if seat_type == 'lower berth':

            score += 150

            reasons.append(

                'Lower berth prioritized '
                'for easier access.'

            )


    # ========================================================
    # 7. BERTH PREFERENCE
    # ========================================================

    if berth_matches(

        passenger,

        seat

    ):

        score += 150

        reasons.append(

            'Passenger berth preference matched.'

        )


    # ========================================================
    # 8. SAME COACH PRIORITY
    # ========================================================

    if is_same_coach(

        coach,

        allocated_seats

    ):

        score += 100

        reasons.append(

            'Passenger allocated in the same coach '
            'as group members.'

        )


    # ========================================================
    # 9. NEARBY SEAT PRIORITY
    # ========================================================

    seat_distance = calculate_seat_distance(

        seat,

        coach,

        allocated_seats

    )

    if seat_distance is not None:

        if seat_distance == 1:

            score += 100

            reasons.append(

                'Seat is immediately close '
                'to another passenger.'

            )

        elif seat_distance == 2:

            score += 80

            reasons.append(

                'Seat is very close '
                'to another passenger.'

            )

        elif seat_distance <= 4:

            score += 50

            reasons.append(

                'Seat is reasonably close '
                'to another passenger.'

            )

        elif seat_distance <= 8:

            score += 20

            reasons.append(

                'Seat is within the same nearby area.'

            )


    # ========================================================
    # 10. GENERAL COMFORT
    # ========================================================

    if is_comfort_seat(

        seat

    ):

        score += 10

        reasons.append(

            'Seat provides additional general comfort.'

        )


    return {

        'score':
            score,

        'reasons':
            reasons

    }


# ============================================================
# FILTER ELIGIBLE SEATS
# ============================================================

def get_eligible_seats(
    passenger,
    available_seats
):

    eligible_seats = []

    for item in available_seats:

        seat = item[

            'seat'

        ]

        coach = item[

            'coach'

        ]

        if not coach_type_matches(

            passenger,

            coach

        ):

            continue

        eligible_seats.append(

            item

        )

    return eligible_seats


# ============================================================
# FIND BEST SEAT
# ============================================================

def find_best_seat(
    passenger,
    available_seats,
    allocated_seats
):

    eligible_seats = get_eligible_seats(

        passenger,

        available_seats

    )

    if not eligible_seats:

        return None

    scored_seats = []

    for item in eligible_seats:

        seat = item[

            'seat'

        ]

        coach = item[

            'coach'

        ]

        score_data = calculate_seat_score(

            passenger=

                passenger,

            seat=

                seat,

            coach=

                coach,

            allocated_seats=

                allocated_seats

        )

        scored_seats.append({

            'item':
                item,

            'score':
                score_data[
                    'score'
                ],

            'reasons':
                score_data[
                    'reasons'
                ]

        })


    scored_seats.sort(

        key=lambda item:

            item[

                'score'

            ],

        reverse=True

    )


    return scored_seats[

        0

    ]


# ============================================================
# CALCULATE PREFERENCE MATCHING PERCENTAGE
# ============================================================

def calculate_matching_percentage(
    passenger,
    selected_seat,
    selected_coach,
    allocated_seats,
    explicit_seat_fulfilled
):

    total_points = 0

    earned_points = 0


    # ========================================================
    # BERTH PREFERENCE
    # ========================================================

    berth_preference = normalize_text(

        passenger.get(
            'berth_preference'
        )

    )

    if berth_preference:

        total_points += 30

        if berth_matches(

            passenger,

            selected_seat

        ):

            earned_points += 30


    # ========================================================
    # EXPLICIT SEAT SELECTION
    # ========================================================

    if has_explicit_seat_preference(

        passenger

    ):

        total_points += 30

        if explicit_seat_fulfilled:

            earned_points += 30


    # ========================================================
    # PRIORITY COMFORT
    # ========================================================

    priority = get_passenger_priority(

        passenger

    )

    if priority != 'normal':

        total_points += 30

        if is_comfort_seat(

            selected_seat

        ):

            earned_points += 30


    # ========================================================
    # GROUP SAME COACH
    # ========================================================

    if allocated_seats:

        total_points += 10

        if is_same_coach(

            selected_coach,

            allocated_seats

        ):

            earned_points += 10


    # ========================================================
    # NO SPECIAL PREFERENCES
    # ========================================================

    if total_points == 0:

        return 100


    return round(

        (
            earned_points
            /
            total_points
        )
        *
        100

    )


# ============================================================
# ALLOCATE SEATS FOR ALL PASSENGERS
# ============================================================

def allocate_seats_for_passengers(
    passengers,
    available_seats
):

    remaining_seats = list(

        available_seats

    )

    allocated_seats = []


    # ========================================================
    # PASSENGER PRIORITY ORDER
    # ========================================================

    priority_order = {

        'person with disability':
            5,

        'pregnant woman':
            4,

        'lactating mother':
            3,

        'senior citizen':
            2,

        'medical':
            2,

        'normal':
            1,

    }


    # ========================================================
    # SORT PASSENGERS
    # ========================================================

    sorted_passengers = sorted(

        enumerate(

            passengers

        ),

        key=lambda item:

            (

                has_explicit_seat_preference(

                    item[1]

                ),

                priority_order.get(

                    get_passenger_priority(

                        item[1]

                    ),

                    1

                )

            ),

        reverse=True

    )


    # ========================================================
    # ALLOCATE SEATS
    # ========================================================

    for original_index, passenger in sorted_passengers:

        best_option = find_best_seat(

            passenger=

                passenger,

            available_seats=

                remaining_seats,

            allocated_seats=

                allocated_seats

        )


        if best_option is None:

            return {

                'success':
                    False,

                'allocated_seats':
                    allocated_seats,

                'message':
                    (
                        'Unable to allocate a suitable '
                        'seat for Passenger '
                        f'{original_index + 1}.'
                    )

            }


        selected_item = best_option[

            'item'

        ]

        selected_seat = selected_item[

            'seat'

        ]

        selected_coach = selected_item[

            'coach'

        ]


        remaining_seats.remove(

            selected_item

        )


        # ====================================================
        # EXPLICIT SEAT EVALUATION
        # ====================================================

        preferred_seat_id = passenger.get(

            'preferred_seat_id'

        )

        try:

            preferred_seat_id = int(

                preferred_seat_id

            )

        except (
            TypeError,
            ValueError
        ):

            preferred_seat_id = None


        explicit_seat_fulfilled = (

            preferred_seat_id is not None
            and
            preferred_seat_id
            ==
            selected_seat.id

        )


        # ====================================================
        # BERTH EVALUATION
        # ====================================================

        has_berth_preference = bool(

            normalize_text(

                passenger.get(
                    'berth_preference'
                )

            )

        )

        berth_preference_fulfilled = (

            has_berth_preference
            and
            berth_matches(

                passenger,

                selected_seat

            )

        )


        # ====================================================
        # SAME COACH EVALUATION
        # ====================================================

        same_coach_as_group = is_same_coach(

            selected_coach,

            allocated_seats

        )


        # ====================================================
        # COMFORT EVALUATION
        # ====================================================

        comfort_seat_allocated = is_comfort_seat(

            selected_seat

        )


        # ====================================================
        # MATCHING PERCENTAGE
        # ====================================================

        matching_percentage = calculate_matching_percentage(

            passenger=

                passenger,

            selected_seat=

                selected_seat,

            selected_coach=

                selected_coach,

            allocated_seats=

                allocated_seats,

            explicit_seat_fulfilled=

                explicit_seat_fulfilled

        )


        # ====================================================
        # STORE ALLOCATION RESULT
        # ====================================================

        allocated_seats.append({

            'passenger_index':

                original_index,

            'passenger':

                passenger,

            'seat_id':

                selected_seat.id,

            'seat_number':

                selected_seat.seat_number,

            'seat_type':

                selected_seat.get_seat_type_display(),

            'coach_id':

                selected_coach.id,

            'coach_number':

                selected_coach.coach_number,

            'coach_type':

                selected_coach.get_coach_type_display(),

            # ------------------------------------------------
            # PRIORITY INFORMATION
            # ------------------------------------------------

            'priority':

                get_passenger_priority(

                    passenger

                ),

            'priority_display':

                get_priority_display(

                    passenger

                ),

            # ------------------------------------------------
            # BERTH INFORMATION
            # ------------------------------------------------

            'berth_preference':

                get_requested_berth(

                    passenger

                ),

            'berth_preference_fulfilled':

                berth_preference_fulfilled,

            # ------------------------------------------------
            # EXPLICIT SEAT INFORMATION
            # ------------------------------------------------

            'was_explicitly_selected':

                has_explicit_seat_preference(

                    passenger

                ),

            'explicit_seat_fulfilled':

                explicit_seat_fulfilled,

            # ------------------------------------------------
            # GROUP INFORMATION
            # ------------------------------------------------

            'same_coach_as_group':

                same_coach_as_group,

            # ------------------------------------------------
            # COMFORT INFORMATION
            # ------------------------------------------------

            'comfort_seat_allocated':

                comfort_seat_allocated,

            # ------------------------------------------------
            # MATCHING PERCENTAGE
            # ------------------------------------------------

            'preference_matching_percentage':

                matching_percentage,

            # ------------------------------------------------
            # INTERNAL ALGORITHM DATA
            # ------------------------------------------------

            'score':

                best_option[

                    'score'

                ],

            'allocation_reasons':

                best_option[

                    'reasons'

                ],

        })


    # ========================================================
    # RESTORE ORIGINAL PASSENGER ORDER
    # ========================================================

    allocated_seats.sort(

        key=lambda item:

            item[

                'passenger_index'

            ]

    )


    # ========================================================
    # RETURN RESULT
    # ========================================================

    return {

        'success':

            True,

        'allocated_seats':

            allocated_seats,

        'message':

            (
                'Seats successfully allocated '
                'using the intelligent seat allocation algorithm.'
            )

    }