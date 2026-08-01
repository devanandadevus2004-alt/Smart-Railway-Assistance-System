from decimal import Decimal


# ============================================================
# FALLBACK DISTANCE
# ============================================================

# Used only when actual source-to-destination distance
# is not available in TrainStopDistance.
AVERAGE_DISTANCE_PER_SEGMENT = Decimal("32.20")


# ============================================================
# APPROXIMATE FARE PER KM
# ============================================================

FARE_PER_KM = {

    "GEN":
        Decimal("0.35"),

    "SL":
        Decimal("0.50"),

    "3A":
        Decimal("1.10"),

    "2A":
        Decimal("1.60"),

    "1A":
        Decimal("2.50"),

    "CC":
        Decimal("1.00"),

    "EC":
        Decimal("1.80"),

}


# ============================================================
# MINIMUM FARE
# ============================================================

MINIMUM_FARE = {

    "GEN":
        Decimal("30.00"),

    "SL":
        Decimal("145.00"),

    "3A":
        Decimal("300.00"),

    "2A":
        Decimal("500.00"),

    "1A":
        Decimal("700.00"),

    "CC":
        Decimal("250.00"),

    "EC":
        Decimal("400.00"),

}


# ============================================================
# RESERVATION CHARGES
# ============================================================

RESERVATION_CHARGE = {

    "GEN":
        Decimal("0.00"),

    "SL":
        Decimal("20.00"),

    "3A":
        Decimal("40.00"),

    "2A":
        Decimal("50.00"),

    "1A":
        Decimal("60.00"),

    "CC":
        Decimal("40.00"),

    "EC":
        Decimal("60.00"),

}


# ============================================================
# FARE CALCULATOR
# ============================================================

def calculate_fare(
    distance=None,
    stop_segments=0,
    coach_type="SL",
):

    # --------------------------------------------------------
    # Validate coach type
    # --------------------------------------------------------

    if coach_type not in FARE_PER_KM:

        coach_type = "SL"


    # --------------------------------------------------------
    # Convert distance
    # --------------------------------------------------------

    if distance is not None:

        try:

            distance = Decimal(
                str(distance)
            )

        except (
            ValueError,
            TypeError
        ):

            distance = None


    # --------------------------------------------------------
    # ACTUAL DISTANCE AVAILABLE
    # --------------------------------------------------------

    if (

        distance is not None

        and

        distance > 0

    ):

        journey_distance = distance

        distance_source = "Actual"


    # --------------------------------------------------------
    # FALLBACK DISTANCE
    # --------------------------------------------------------

    else:

        try:

            stop_segments = int(
                stop_segments
            )

        except (
            ValueError,
            TypeError
        ):

            stop_segments = 0


        if stop_segments < 0:

            stop_segments = 0


        journey_distance = (

            Decimal(
                str(stop_segments)
            )

            *

            AVERAGE_DISTANCE_PER_SEGMENT

        )

        distance_source = "Estimated"


    # --------------------------------------------------------
    # Minimum distance
    # --------------------------------------------------------

    if journey_distance < 1:

        journey_distance = Decimal(
            "1.00"
        )


    # --------------------------------------------------------
    # Fare rate
    # --------------------------------------------------------

    rate_per_km = FARE_PER_KM[
        coach_type
    ]


    # --------------------------------------------------------
    # Calculate base fare
    # --------------------------------------------------------

    base_fare = (

        journey_distance

        *

        rate_per_km

    )


    base_fare = base_fare.quantize(

        Decimal("0.01")

    )


    # --------------------------------------------------------
    # Minimum fare
    # --------------------------------------------------------

    minimum_fare = MINIMUM_FARE[
        coach_type
    ]


    if base_fare < minimum_fare:

        base_fare = minimum_fare


    # --------------------------------------------------------
    # Reservation charge
    # --------------------------------------------------------

    reservation_charge = (

        RESERVATION_CHARGE[
            coach_type
        ]

    )


    # --------------------------------------------------------
    # Superfast charge
    # --------------------------------------------------------

    superfast_charge = Decimal(
        "0.00"
    )


    # --------------------------------------------------------
    # Total fare
    # --------------------------------------------------------

    total_fare = (

        base_fare

        +

        reservation_charge

        +

        superfast_charge

    )


    total_fare = total_fare.quantize(

        Decimal("0.01")

    )


    # --------------------------------------------------------
    # Return result
    # --------------------------------------------------------

    return {

        "distance":
            journey_distance,

        "distance_source":
            distance_source,

        "coach_type":
            coach_type,

        "base_fare":
            base_fare,

        "reservation_charge":
            reservation_charge,

        "superfast_charge":
            superfast_charge,

        "total_fare":
            total_fare,

    }