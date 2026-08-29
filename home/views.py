from django.shortcuts import render, redirect
from django.contrib import messages
from .models import Passenger
from .models import Passenger, LuggageBooking
from .models import Passenger, LuggageBooking, Station,LuggageItem,StationFacility
from .models import Officer
from datetime import datetime, time
from django.utils import timezone
from django.shortcuts import get_object_or_404, redirect, render
from datetime import timedelta
from django.http import JsonResponse
from ticket_booking.models import TicketBooking,SeatReservation


def booking_details(request, booking_id):

    booking = get_object_or_404(
        LuggageBooking,
        id=booking_id
    )

    today = timezone.localdate()

    # Verification must be completed at least
    # 2 days before the passenger's travel date.
    latest_verification_date = (
        booking.travel_date - timedelta(days=2)
    )

    # Verification cannot be scheduled in the past.
    verification_min_date = today

    # If the calculated latest date is before today,
    # there is no valid verification window.
    verification_max_date = latest_verification_date

    return render(
        request,
        "home/booking_details.html",
        {
            "booking": booking,
            "verification_min_date":
                verification_min_date,
            "verification_max_date":
                verification_max_date,
        }
    )


def update_booking(request, booking_id):

    booking = get_object_or_404(
        LuggageBooking,
        id=booking_id
    )

    if request.method == "POST":

        action = request.POST.get("action")

        if action == "accept":

            verification_date = request.POST.get(
                "verification_date"
            )

            verification_time = request.POST.get(
                "verification_time"
            )

            instructions = request.POST.get(
                "instructions"
            )

            # Make sure both date and time are provided
            if not verification_date or not verification_time:

                return render(
                    request,
                    "home/booking_details.html",
                    {
                        "booking": booking,
                        "error":
                            "Please select verification date and time."
                    }
                )

            # Convert submitted values
            verification_date_obj = datetime.strptime(
                verification_date,
                "%Y-%m-%d"
            ).date()

            verification_time_obj = datetime.strptime(
                verification_time,
                "%H:%M"
            ).time()

            today = timezone.localdate()

            # Verification cannot be in the past
            if verification_date_obj < today:

                return render(
                    request,
                    "home/booking_details.html",
                    {
                        "booking": booking,
                        "error":
                            "Verification date cannot be in the past."
                    }
                )

            # Verification must be before travel date
            if verification_date_obj >= booking.travel_date:

                return render(
                    request,
                    "home/booking_details.html",
                    {
                        "booking": booking,
                        "error":
                            "Verification must be scheduled "
                            "before the passenger's travel date."
                    }
                )

            # Officer duty hours: 9 AM - 5 PM
            duty_start = time(9, 0)
            duty_end = time(17, 0)

            if not (
                duty_start
                <= verification_time_obj
                < duty_end
            ):

                return render(
                    request,
                    "home/booking_details.html",
                    {
                        "booking": booking,
                        "error":
                            "Verification time must be "
                            "within officer duty hours "
                            "(9:00 AM - 5:00 PM)."
                    }
                )

            # Check whether this officer already has
            # another booking at the same date and time.
            officer = Officer.objects.get(
                id=request.session["officer_id"]
            )

            existing_booking = LuggageBooking.objects.filter(
                source_station=officer.station,
                verification_date=verification_date_obj,
                verification_time=verification_time_obj,
                status="Verification Scheduled"
            ).exclude(
                id=booking.id
            ).first()

            # Existing allocation found
            if existing_booking:

                # Officer has not yet confirmed that
                # they want to handle multiple passengers.
                proceed = request.POST.get(
                    "proceed_multiple"
                )

                if proceed != "yes":

                    return render(
                        request,
                        "home/booking_details.html",
                        {
                            "booking": booking,
                            "error":
                                "This verification time is "
                                "already allocated to another "
                                "passenger.",
                            "existing_booking":
                                existing_booking,
                            "verification_date":
                                verification_date,
                            "verification_time":
                                verification_time,
                            "instructions":
                                instructions,
                            "show_multiple_warning":
                                True,
                        }
                    )

            # Schedule the verification
            booking.status = "Verification Scheduled"

            booking.verification_date = (
                verification_date_obj
            )

            booking.verification_time = (
                verification_time_obj
            )

            booking.instructions = instructions

            booking.rejection_reason = ""

        elif action == "reject":

            booking.status = "Rejected"

            booking.rejection_reason = request.POST.get(
                "rejection_reason"
            )

            booking.verification_date = None

            booking.verification_time = None

            booking.instructions = ""

        booking.save()

    return redirect("officer_dashboard")


def home(request):
    return render(request, "home/index.html")
def login(request):
    print("Method:", request.method)

    if request.method == "POST":
        username = request.POST["username"]
        password = request.POST["password"]

        try:
            passenger = Passenger.objects.get(
                username=username,
                password=password
            )
            request.session["passenger_id"] = passenger.id
            request.session["passenger_name"] = passenger.full_name
            return redirect("dashboard")

        except Passenger.DoesNotExist:
            messages.error(request, "Invalid Username or Password")
            return redirect("login")

    print("GET request")
    return render(request, "home/login.html")

def register(request):
    if request.method == "POST":
        full_name = request.POST["full_name"]
        email = request.POST["email"]
        username = request.POST["username"]
        aadhaar_number = request.POST["aadhaar_number"]
        phone_number = request.POST["phone_number"]
        gender = request.POST["gender"]
        address = request.POST["address"]
        password = request.POST["password"]
        confirm_password = request.POST["confirm_password"]

        # Check password
        if password != confirm_password:
             return render(request, "home/register.html", {
        "error": "Passwords do not match!",
        "full_name": full_name,
        "email": email,
        "username": username,
        "aadhaar_number": aadhaar_number,
        "phone_number": phone_number,
        "gender": gender,
        "address": address,
    })

        # Check username
        if Passenger.objects.filter(username=username).exists():
            return render(request, "home/register.html", {
                "error": "Username already exists!"
            })

        # Check email
        if Passenger.objects.filter(email=email).exists():
            return render(request, "home/register.html", {
                "error": "Email already exists!",
                 "full_name": full_name,
                "email": email,
                 "username": username,
                 "aadhaar_number": aadhaar_number,
                "phone_number": phone_number,
                 "gender": gender,
                "address": address,
    })

        # Check Aadhaar
        if Passenger.objects.filter(aadhaar_number=aadhaar_number).exists():
            return render(request, "home/register.html", {
            "error": "Some error",
            "full_name": full_name,
            "email": email,
            "username": username,
             "aadhaar_number": aadhaar_number,
             "phone_number": phone_number,
             "gender": gender,
            "address": address,
        })

        if not aadhaar_number.isdigit() or len(aadhaar_number) != 12:
          return render(request, "home/register.html", {
        "error": "Some error",
        "full_name": full_name,
        "email": email,
        "username": username,
        "aadhaar_number": aadhaar_number,
        "phone_number": phone_number,
        "gender": gender,
        "address": address,
        })

        if not phone_number.isdigit() or len(phone_number) != 10:
            return render(request, "home/register.html", {
            "error": "Some error",
            "full_name": full_name,
            "email": email,
            "username": username,
            "aadhaar_number": aadhaar_number,
            "phone_number": phone_number,
            "gender": gender,
            "address": address,
        })

        Passenger.objects.create(
            full_name=full_name,
            email=email,
            username=username,
            password=password,
            aadhaar_number=aadhaar_number,
            phone_number=phone_number,
            gender=gender,
            address=address,
        )

        return render(request, "home/register.html", {
            "success": "Registration Successful!"
        })

    return render(request, "home/register.html")
def logout(request):
    request.session.flush()
    return redirect("home")
def dashboard(request):
    if "passenger_id" not in request.session:
        return redirect("login")

    return render(request, "home/dashboard.html", {
        "name": request.session["passenger_name"]
    })
def luggage_booking(request):

    stations = Station.objects.all()

    today = timezone.localdate()

    # WITHOUT_TICKET existing rule
    minimum_travel_date = today + timedelta(days=2)

    # WITH_TICKET new rule
    minimum_ticket_booking_date = today + timedelta(days=5)

    STANDARD_PARCEL_MAX_WEIGHT = 150

    # =========================================================
    # GET REQUEST
    # =========================================================

    if request.method == "GET":

        return render(
            request,
            "home/luggage_booking.html",
            {
                "stations": stations,
                "minimum_travel_date": minimum_travel_date,
            }
        )

    # =========================================================
    # POST REQUEST
    # =========================================================

    try:

        # -----------------------------------------------------
        # BASIC FORM DATA
        # -----------------------------------------------------

        transfer_type = request.POST.get(
            "transfer_type"
        )

        contact_number = request.POST.get(
            "contact_number"
        )

        passenger = Passenger.objects.get(
            id=request.session["passenger_id"]
        )

    except Passenger.DoesNotExist:

        return render(
            request,
            "home/luggage_booking.html",
            {
                "stations": stations,
                "error": "Passenger account could not be found.",
                "minimum_travel_date": minimum_travel_date,
            }
        )

    # =========================================================
    # VARIABLES THAT WILL BE SET DEPENDING ON TRANSFER TYPE
    # =========================================================

    ticket_booking = None

    source_station = None
    destination_station = None
    travel_date = None
    # =========================================================
# WITH TICKET
# =========================================================

    if transfer_type == "WITH_TICKET":

    # -----------------------------------------------------
    # GET TICKET BOOKING ID
    # -----------------------------------------------------

        ticket_booking_id = request.POST.get(
            "ticket_booking_id"
        )

        if not ticket_booking_id:

            return render(
                request,
                "home/luggage_booking.html",
                {
                    "stations": stations,
                    "error": (
                        "Please enter your confirmed "
                        "Ticket Booking ID."
                    ),
                    "minimum_travel_date":
                        minimum_travel_date,
                }
            )

        # -----------------------------------------------------
        # RETRIEVE TICKET
        # -----------------------------------------------------

        try:

            ticket_booking = TicketBooking.objects.get(
                id=ticket_booking_id,
                passenger=passenger
            )

        except TicketBooking.DoesNotExist:

            return render(
                request,
                "home/luggage_booking.html",
                {
                    "stations": stations,
                    "error": (
                        "The Ticket Booking ID is invalid "
                        "or does not belong to your account."
                    ),
                    "minimum_travel_date":
                        minimum_travel_date,
                }
            )

        # -----------------------------------------------------
        # CHECK TICKET STATUS
        # -----------------------------------------------------

        if ticket_booking.status != "CONFIRMED":

            return render(
                request,
                "home/luggage_booking.html",
                {
                    "stations": stations,
                    "error": (
                        "Luggage transfer is available "
                        "only for confirmed railway tickets. "
                        f"Current ticket status: "
                        f"{ticket_booking.status}."
                    ),
                    "minimum_travel_date":
                        minimum_travel_date,
                }
            )

        # -----------------------------------------------------
        # GET JOURNEY DATE FROM TICKET
        # -----------------------------------------------------

        travel_date = ticket_booking.travel_date

        # -----------------------------------------------------
        # CHECK WHETHER JOURNEY HAS EXPIRED
        # -----------------------------------------------------

        if travel_date < today:

            return render(
                request,
                "home/luggage_booking.html",
                {
                    "stations": stations,
                    "error": (
                        "Luggage transfer cannot be booked "
                        "because the ticket journey date "
                        "has already expired."
                    ),
                    "minimum_travel_date":
                        minimum_travel_date,
                }
            )

        # -----------------------------------------------------
        # CHECK 5-DAY ADVANCE REQUIREMENT
        # -----------------------------------------------------

        days_remaining = (
            travel_date - today
        ).days

        if days_remaining < 5:

            return render(
                request,
                "home/luggage_booking.html",
                {
                    "stations": stations,
                    "error": (
                        "Luggage transfer must be booked "
                        "at least 5 days before the "
                        "ticket journey date. "
                        f"Your journey is only "
                        f"{days_remaining} day(s) away."
                    ),
                    "minimum_travel_date":
                        minimum_travel_date,
                }
            )

        # -----------------------------------------------------
        # GET SOURCE AND DESTINATION FROM TRAIN
        # -----------------------------------------------------

        # -----------------------------------------------------
# GET PASSENGER'S ACTUAL SOURCE AND DESTINATION
# FROM SEAT RESERVATION
# -----------------------------------------------------
        seat_reservation = (
            SeatReservation.objects
            .filter(
                booking_id=ticket_booking.id,
                status="BOOKED"
            )
            .select_related(
                "source_station",
                "destination_station"
            )
            .first()
        )

        if not seat_reservation:

            return render(
                request,
                "home/luggage_booking.html",
                {
                    "stations": stations,
                    "error": (
                        "No seat reservation was found "
                        "for this ticket booking."
                    ),
                    "minimum_travel_date":
                        minimum_travel_date,
                }
            )

        source_station = (
            seat_reservation.source_station
        )

        destination_station = (
            seat_reservation.destination_station
        )

        # -----------------------------------------------------
        # PREPARE TICKET INFORMATION FOR DISPLAY
        # -----------------------------------------------------

        ticket_information = {

            "booking_id":
                ticket_booking.id,

            "train":
                ticket_booking.train,

            "passenger":
                passenger,

            "travel_date":
                ticket_booking.travel_date,

            "source_station":
                source_station,

            "destination_station":
                destination_station,

            "status":
                ticket_booking.status,
    }

    # =========================================================
    # WITHOUT TICKET
    # =========================================================

    elif transfer_type == "WITHOUT_TICKET":

        # -----------------------------------------------------
        # SOURCE
        # -----------------------------------------------------

        try:

            source_station = Station.objects.get(
                id=request.POST["source_station"]
            )

            destination_station = Station.objects.get(
                id=request.POST["destination_station"]
            )

        except (
            Station.DoesNotExist,
            KeyError
        ):

            return render(
                request,
                "home/luggage_booking.html",
                {
                    "stations": stations,
                    "error": (
                        "Invalid source or destination station."
                    ),
                    "minimum_travel_date":
                        minimum_travel_date,
                }
            )

        # -----------------------------------------------------
        # SAME STATION CHECK
        # -----------------------------------------------------

        if source_station.id == destination_station.id:

            return render(
                request,
                "home/luggage_booking.html",
                {
                    "stations": stations,
                    "error": (
                        "Source Station and Destination "
                        "Station cannot be the same. "
                        "Please select different stations."
                    ),
                    "minimum_travel_date":
                        minimum_travel_date,
                }
            )

        # -----------------------------------------------------
        # TRAVEL DATE
        # -----------------------------------------------------

        travel_date_string = request.POST.get(
            "travel_date"
        )

        try:

            travel_date = datetime.strptime(
                travel_date_string,
                "%Y-%m-%d"
            ).date()

        except (
            TypeError,
            ValueError
        ):

            return render(
                request,
                "home/luggage_booking.html",
                {
                    "stations": stations,
                    "error":
                        "Please enter a valid travel date.",
                    "minimum_travel_date":
                        minimum_travel_date,
                }
            )

        # -----------------------------------------------------
        # EXISTING 2-DAY RULE
        # -----------------------------------------------------

        if travel_date < minimum_travel_date:

            return render(
                request,
                "home/luggage_booking.html",
                {
                    "stations": stations,
                    "error": (
                        "Luggage transfer requests must be "
                        "submitted at least 2 days before "
                        "the travel date."
                    ),
                    "minimum_travel_date":
                        minimum_travel_date,
                }
            )

    # =========================================================
    # INVALID TRANSFER TYPE
    # =========================================================

    else:

        return render(
            request,
            "home/luggage_booking.html",
            {
                "stations": stations,
                "error":
                    "Please select a valid transfer type.",
                "minimum_travel_date":
                    minimum_travel_date,
            }
        )

    # =========================================================
    # NUMBER OF ITEMS
    # =========================================================

    try:

        number_of_items = int(
            request.POST.get(
                "number_of_items",
                0
            )
        )

    except (
        TypeError,
        ValueError
    ):

        number_of_items = 0

    if number_of_items <= 0:

        return render(
            request,
            "home/luggage_booking.html",
            {
                "stations": stations,
                "error": (
                    "Please enter at least one "
                    "luggage item."
                ),
                "minimum_travel_date":
                    minimum_travel_date,
            }
        )

    # =========================================================
    # COLLECT INDIVIDUAL ITEMS
    # =========================================================

    luggage_items = []

    total_weight = 0

    for i in range(
        1,
        number_of_items + 1
    ):

        # -----------------------------------------------------
        # ITEM TYPE
        # -----------------------------------------------------

        luggage_type = request.POST.get(
            f"item_type_{i}"
        )

        # -----------------------------------------------------
        # ITEM WEIGHT
        # -----------------------------------------------------

        weight_value = request.POST.get(
            f"item_weight_{i}"
        )

        # -----------------------------------------------------
        # DESCRIPTION
        # -----------------------------------------------------

        item_description = request.POST.get(
            f"item_description_{i}",
            ""
        ).strip()

        # -----------------------------------------------------
        # IMAGE
        # -----------------------------------------------------

        item_image = request.FILES.get(
            f"item_image_{i}"
        )

        # -----------------------------------------------------
        # TYPE / WEIGHT CHECK
        # -----------------------------------------------------

        if not luggage_type or not weight_value:

            return render(
                request,
                "home/luggage_booking.html",
                {
                    "stations": stations,
                    "error": (
                        f"Please enter the type and "
                        f"weight for Item {i}."
                    ),
                    "minimum_travel_date":
                        minimum_travel_date,
                }
            )

        # -----------------------------------------------------
        # WEIGHT VALIDATION
        # -----------------------------------------------------

        try:

            item_weight = float(
                weight_value
            )

        except (
            TypeError,
            ValueError
        ):

            return render(
                request,
                "home/luggage_booking.html",
                {
                    "stations": stations,
                    "error": (
                        f"Please enter a valid weight "
                        f"for Item {i}."
                    ),
                    "minimum_travel_date":
                        minimum_travel_date,
                }
            )

        if item_weight <= 0:

            return render(
                request,
                "home/luggage_booking.html",
                {
                    "stations": stations,
                    "error": (
                        f"Weight for Item {i} "
                        f"must be greater than zero."
                    ),
                    "minimum_travel_date":
                        minimum_travel_date,
                }
            )

        # -----------------------------------------------------
        # 150 KG CHECK
        # ONLY WITHOUT TICKET
        # -----------------------------------------------------

        if (
            transfer_type == "WITHOUT_TICKET"
            and
            item_weight >
            STANDARD_PARCEL_MAX_WEIGHT
        ):

            return render(
                request,
                "home/luggage_booking.html",
                {
                    "stations": stations,
                    "error": (
                        f"Item {i} weighs "
                        f"{item_weight} kg. "
                        f"The normal maximum for "
                        f"a single parcel package "
                        f"is "
                        f"{STANDARD_PARCEL_MAX_WEIGHT} kg. "
                        "Packages exceeding this "
                        "limit require applicable "
                        "railway permission."
                    ),
                    "minimum_travel_date":
                        minimum_travel_date,
                }
            )

        # -----------------------------------------------------
        # OTHER ITEM VALIDATION
        # -----------------------------------------------------

        if luggage_type == "Other":

            if not item_description:

                return render(
                    request,
                    "home/luggage_booking.html",
                    {
                        "stations": stations,
                        "error": (
                            f"Please provide a "
                            f"description for "
                            f"Item {i}."
                        ),
                        "minimum_travel_date":
                            minimum_travel_date,
                    }
                )

            if not item_image:

                return render(
                    request,
                    "home/luggage_booking.html",
                    {
                        "stations": stations,
                        "error": (
                            f"Please upload an "
                            f"image for Item {i}."
                        ),
                        "minimum_travel_date":
                            minimum_travel_date,
                    }
                )

        # -----------------------------------------------------
        # STORE ITEM DATA
        # -----------------------------------------------------

        luggage_items.append({

            "item_number":
                i,

            "luggage_type":
                luggage_type,

            "weight":
                item_weight,

            "item_description":
                item_description,

            "item_image":
                item_image,

        })

        total_weight += item_weight

    # =========================================================
    # SAVE MAIN LUGGAGE BOOKING
    # =========================================================

    main_luggage_type = luggage_items[0][
        "luggage_type"
    ]

    booking = LuggageBooking.objects.create(

        passenger=passenger,

        transfer_type=transfer_type,

        ticket_booking=ticket_booking,

        # WITH_TICKET:
        # These came directly from ticket.
        #
        # WITHOUT_TICKET:
        # These came from passenger selection.
        source_station=source_station,

        destination_station=destination_station,

        luggage_type=main_luggage_type,

        number_of_bags=number_of_items,

        weight=total_weight,

        # WITH_TICKET:
        # This is ticket travel date.
        #
        # WITHOUT_TICKET:
        # This is passenger-entered travel date.
        travel_date=travel_date,

        contact_number=contact_number,

        # Existing default is Pending.
        status="Pending",
    )

    # =========================================================
    # SAVE INDIVIDUAL LUGGAGE ITEMS
    # =========================================================

    for item in luggage_items:

        LuggageItem.objects.create(

            booking=booking,

            item_number=item[
                "item_number"
            ],

            luggage_type=item[
                "luggage_type"
            ],

            weight=item[
                "weight"
            ],

            item_description=item[
                "item_description"
            ],

            item_image=item[
                "item_image"
            ],

        )

    # =========================================================
    # SUCCESS
    # =========================================================

    return render(
        request,
        "home/luggage_booking.html",
        {
            "stations": stations,

            "success": (
                "Luggage booking request submitted "
                "successfully. Your request has been "
                "sent to the officer for verification."
            ),

            "minimum_travel_date":
                minimum_travel_date,
        }
    )
def my_bookings(request):
    passenger = Passenger.objects.get(id=request.session["passenger_id"])

    bookings = LuggageBooking.objects.filter(passenger=passenger)

    return render(request, "home/my_bookings.html", {
        "bookings": bookings
    })
def officer_login(request):

    if request.method == "POST":
        username = request.POST["username"]
        password = request.POST["password"]

        try:
            officer = Officer.objects.get(
                username=username,
                password=password
            )

            request.session["officer_id"] = officer.id
            request.session["officer_name"] = officer.full_name

            return redirect("officer_dashboard")

        except Officer.DoesNotExist:
            return render(request, "home/officer_login.html", {
                "error": "Invalid Username or Password"
            })

    return render(request, "home/officer_login.html")
def officer_dashboard(request):

    if "officer_id" not in request.session:
        return redirect("officer_login")

    officer = Officer.objects.get(id=request.session["officer_id"])

    bookings = LuggageBooking.objects.filter(
        source_station=officer.station
    )

    return render(request, "home/officer_dashboard.html", {
        "officer": officer,
        "bookings": bookings,
    })





from datetime import timedelta
from django.utils import timezone
from django.shortcuts import get_object_or_404, render


def booking_details(request, booking_id):

    booking = get_object_or_404(
        LuggageBooking,
        id=booking_id
    )

    # Current date
    today = timezone.localdate()

    # Officer can schedule verification from today
    # until one day before the passenger's travel date.
    verification_min_date = today

    verification_max_date = (
        booking.travel_date - timedelta(days=1)
    )

    return render(
        request,
        "home/booking_details.html",
        {
            "booking": booking,
            "verification_min_date":
                verification_min_date,
            "verification_max_date":
                verification_max_date,
        }
    )


def update_booking(request, booking_id):

    booking = get_object_or_404(
        LuggageBooking,
        id=booking_id
    )

    if request.method == "POST":

        action = request.POST.get("action")

        if action == "accept":

            verification_date = request.POST.get(
                "verification_date"
            )

            verification_time = request.POST.get(
                "verification_time"
            )

            instructions = request.POST.get(
                "instructions"
            )

            # Make sure both date and time are provided
            if not verification_date or not verification_time:

                return render(
                    request,
                    "home/booking_details.html",
                    {
                        "booking": booking,
                        "error":
                            "Please select verification date and time."
                    }
                )

            # Convert submitted values
            verification_date_obj = datetime.strptime(
                verification_date,
                "%Y-%m-%d"
            ).date()

            verification_time_obj = datetime.strptime(
                verification_time,
                "%H:%M"
            ).time()

            today = timezone.localdate()

            # Verification cannot be in the past
            if verification_date_obj < today:

                return render(
                    request,
                    "home/booking_details.html",
                    {
                        "booking": booking,
                        "error":
                            "Verification date cannot be in the past."
                    }
                )

            # Verification must be before travel date
            if verification_date_obj >= booking.travel_date:

                return render(
                    request,
                    "home/booking_details.html",
                    {
                        "booking": booking,
                        "error":
                            "Verification must be scheduled "
                            "before the passenger's travel date."
                    }
                )

            # Officer duty hours: 9 AM - 5 PM
            duty_start = time(9, 0)
            duty_end = time(17, 0)

            if not (
                duty_start
                <= verification_time_obj
                < duty_end
            ):

                return render(
                    request,
                    "home/booking_details.html",
                    {
                        "booking": booking,
                        "error":
                            "Verification time must be "
                            "within officer duty hours "
                            "(9:00 AM - 5:00 PM)."
                    }
                )

            # Check whether this officer already has
            # another booking at the same date and time.
            officer = Officer.objects.get(
                id=request.session["officer_id"]
            )

            existing_booking = LuggageBooking.objects.filter(
                source_station=officer.station,
                verification_date=verification_date_obj,
                verification_time=verification_time_obj,
                status="Verification Scheduled"
            ).exclude(
                id=booking.id
            ).first()

            # Existing allocation found
            if existing_booking:

                # Officer has not yet confirmed that
                # they want to handle multiple passengers.
                proceed = request.POST.get(
                    "proceed_multiple"
                )

                if proceed != "yes":

                    return render(
                        request,
                        "home/booking_details.html",
                        {
                            "booking": booking,
                            "error":
                                "This verification time is "
                                "already allocated to another "
                                "passenger.",
                            "existing_booking":
                                existing_booking,
                            "verification_date":
                                verification_date,
                            "verification_time":
                                verification_time,
                            "instructions":
                                instructions,
                            "show_multiple_warning":
                                True,
                        }
                    )

            # Schedule the verification
            booking.status = "Verification Scheduled"

            booking.verification_date = (
                verification_date_obj
            )

            booking.verification_time = (
                verification_time_obj
            )

            booking.instructions = instructions

            booking.rejection_reason = ""

        elif action == "reject":

            booking.status = "Rejected"

            booking.rejection_reason = request.POST.get(
                "rejection_reason"
            )

            booking.verification_date = None

            booking.verification_time = None

            booking.instructions = ""

        booking.save()

    return redirect("officer_dashboard")


def cancel_booking(request, booking_id):
    booking = get_object_or_404(LuggageBooking, id=booking_id)

    if booking.status == "Pending":
        booking.delete()

    return redirect("my_bookings")


from .models import Hospital


def emergency_assistance(request):

    stations = Station.objects.all().order_by("station_name")

    hospitals = None

    selected_station = None

    selected_distance = None

    if request.method == "POST":

        station_id = request.POST.get("station")

        selected_distance = request.POST.get("distance")

        if station_id:

            selected_station = Station.objects.get(id=station_id)

            hospitals = Hospital.objects.filter(
                station=selected_station
            )

            if (
                selected_distance
                and
                selected_distance != "all"
            ):

                hospitals = hospitals.filter(
                    distance_km__lte=selected_distance
                )

            hospitals = hospitals.order_by(
                "distance_km"
            )

    return render(

        request,

        "home/emergency_assistance.html",

        {

            "stations": stations,

            "hospitals": hospitals,

            "selected_station": selected_station,

            "selected_distance": selected_distance,

        }

    )

def hospital_details(request, hospital_id):

    hospital = get_object_or_404(
        Hospital,
        id=hospital_id
    )

    return render(
        request,
        "home/hospital_details.html",
        {
            "hospital": hospital
        }
    )


def update_profile(request):

    passenger_id = request.session.get("passenger_id")

    if not passenger_id:
        return redirect("login")

    passenger = get_object_or_404(
        Passenger,
        id=passenger_id
    )

    if request.method == "POST":

        passenger.full_name = request.POST.get(
            "full_name"
        )

        passenger.email = request.POST.get(
            "email"
        )

        passenger.phone_number = request.POST.get(
            "phone_number"
        )

        passenger.gender = request.POST.get(
            "gender"
        )

        passenger.address = request.POST.get(
            "address"
        )
        passenger.save()

        messages.success(
                request,
                "Your profile has been updated successfully."
                )

        return redirect("update_profile")

    return render(
        request,
        "home/update_profile.html",
        {
            "passenger": passenger
        }
    )

def verify_luggage_ticket(request):

    if request.method != "POST":
        return JsonResponse({
            "success": False,
            "message": "Invalid request."
        })

    # ---------------------------------------------
    # GET LOGGED-IN PASSENGER
    # ---------------------------------------------

    passenger_id = request.session.get("passenger_id")

    if not passenger_id:

        return JsonResponse({
            "success": False,
            "message": "Please login before verifying your ticket."
        })

    # ---------------------------------------------
    # GET TICKET BOOKING ID
    # ---------------------------------------------

    ticket_booking_id = request.POST.get(
        "ticket_booking_id"
    )

    if not ticket_booking_id:

        return JsonResponse({
            "success": False,
            "message": "Please enter a Ticket Booking ID."
        })

    # ---------------------------------------------
    # RETRIEVE TICKET
    # ---------------------------------------------

    try:

        ticket_booking = TicketBooking.objects.select_related(
            "passenger",
            "train",
            "train__source_station",
            "train__destination_station"
        ).get(
            id=ticket_booking_id,
            passenger_id=passenger_id
        )

    except TicketBooking.DoesNotExist:

        return JsonResponse({
            "success": False,
            "message": (
                "Invalid Ticket Booking ID or the ticket "
                "does not belong to your account."
            )
        })

    # ---------------------------------------------
    # CHECK TICKET STATUS
    # ---------------------------------------------

    if ticket_booking.status != "CONFIRMED":

        return JsonResponse({
            "success": False,
            "message": (
                "Luggage transfer is available only "
                "for confirmed railway tickets. "
                f"Current ticket status: "
                f"{ticket_booking.status}."
            )
        })

    # ---------------------------------------------
    # GET TODAY
    # ---------------------------------------------

    today = timezone.localdate()

    travel_date = ticket_booking.travel_date

    # ---------------------------------------------
    # CHECK JOURNEY EXPIRED
    # ---------------------------------------------

    if travel_date < today:

        return JsonResponse({
            "success": False,
            "message": (
                "Luggage transfer cannot be booked "
                "because the ticket journey date "
                "has already expired."
            )
        })

    # ---------------------------------------------
    # CHECK 5-DAY RULE
    # ---------------------------------------------

    days_remaining = (
        travel_date - today
    ).days

    if days_remaining < 5:

        return JsonResponse({
            "success": False,
            "message": (
                "Luggage transfer must be booked "
                "at least 5 days before the ticket "
                "journey date. "
                f"Your journey is only "
                f"{days_remaining} day(s) away."
            )
        })

    # ---------------------------------------------
# GET PASSENGER'S ACTUAL JOURNEY STATIONS
# FROM SEAT RESERVATION
# ---------------------------------------------

    seat_reservation = (
        SeatReservation.objects
        .filter(
            booking_id=ticket_booking.id,
            status="BOOKED"
        )
        .select_related(
            "source_station",
            "destination_station"
        )
        .first()
    )

    if not seat_reservation:

        return JsonResponse({
            "success": False,
            "message": (
                "No seat reservation was found "
                "for this ticket booking."
            )
        })

    source_station = (
        seat_reservation.source_station
    )

    destination_station = (
        seat_reservation.destination_station
    )

    # ---------------------------------------------
    # SUCCESS
    # ---------------------------------------------

    return JsonResponse({

        "success": True,

        "message": "Ticket verified successfully.",

        "ticket": {

            "booking_id":
                ticket_booking.id,

            "train":
                (
                    f"{ticket_booking.train.train_number} - "
                    f"{ticket_booking.train.train_name}"
                ),

            "passenger":
                ticket_booking.passenger.full_name,

            "travel_date":
                travel_date.strftime("%d %b %Y"),

            "source":
                (
                    f"{source_station.station_name} "
                    f"({source_station.station_code})"
                ),

            "destination":
                (
                    f"{destination_station.station_name} "
                    f"({destination_station.station_code})"
                ),

            "status":
                ticket_booking.status,

        }

    })

def about(request):
    return render(request, "home/about.html")

def station_guide(request):

    stations = Station.objects.filter(
    facilities__isnull=False
).distinct()

    selected_station = None
    selected_facility = None

    if request.method == "POST":

        station_id = request.POST.get(
            "station"
        )

        facility_id = request.POST.get(
            "facility"
        )

        # Get selected station
        if station_id:

            try:

                selected_station = Station.objects.get(
                    id=station_id
                )

            except Station.DoesNotExist:

                selected_station = None

        # Get selected facility
        if facility_id:

            try:

                selected_facility = StationFacility.objects.get(
                    id=facility_id,
                    station=selected_station
                )

            except StationFacility.DoesNotExist:

                selected_facility = None

    return render(
        request,
        "home/station_guide.html",
        {
            "stations": stations,
            "selected_station": selected_station,
            "selected_facility": selected_facility,
        }
    )