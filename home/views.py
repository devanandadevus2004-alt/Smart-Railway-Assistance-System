from django.shortcuts import render
from .models import Passenger

def home(request):
    return render(request, "home/index.html")

def login(request):
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