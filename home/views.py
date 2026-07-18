from django.shortcuts import render, redirect
from django.contrib import messages
from .models import Passenger
from .models import Passenger, LuggageBooking
from .models import Passenger, LuggageBooking, Station
from .models import Officer
from django.shortcuts import get_object_or_404, redirect


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

    if request.method == "POST":
        source_station = Station.objects.get(id=request.POST["source_station"])
        destination_station = Station.objects.get(id=request.POST["destination_station"])

        luggage_type = request.POST["luggage_type"]
        number_of_bags = request.POST["number_of_bags"]
        weight = request.POST["weight"]
        travel_date = request.POST["travel_date"]
        contact_number = request.POST["contact_number"]

        passenger = Passenger.objects.get(id=request.session["passenger_id"])

        LuggageBooking.objects.create(
            passenger=passenger,
            source_station=source_station,
            destination_station=destination_station,
            luggage_type=luggage_type,
            number_of_bags=number_of_bags,
            weight=weight,
            travel_date=travel_date,
            contact_number=contact_number,
        )

        return render(request, "home/luggage_booking.html", {
            "stations": stations,
            "success": "Luggage booking submitted successfully!"
        })

    return render(request, "home/luggage_booking.html", {
        "stations": stations
    })
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



def booking_details(request, booking_id):
    booking = LuggageBooking.objects.get(id=booking_id)

    return render(request, "home/booking_details.html", {
        "booking": booking
    })



def update_booking(request, booking_id):
    booking = get_object_or_404(LuggageBooking, id=booking_id)

    if request.method == "POST":
        booking.verification_date = request.POST["verification_date"]
        booking.verification_time = request.POST["verification_time"]
        booking.status = request.POST["status"]
        booking.save()

    return redirect("officer_dashboard")