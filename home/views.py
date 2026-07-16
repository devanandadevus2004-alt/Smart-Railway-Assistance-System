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
            return render(request, "home/index.html", {
                "name": passenger.full_name
            })

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
        password = request.POST["password"]

        Passenger.objects.create(
            full_name=full_name,
            email=email,
            username=username,
            password=password
        )

        return render(request, "home/register.html", {
            "success": "Registration Successful!"
        })

    return render(request, "home/register.html")