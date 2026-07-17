from django.shortcuts import render, redirect
from django.contrib import messages
from .models import Passenger

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