from django.db import models


class Station(models.Model):
    station_name = models.CharField(max_length=100)
    station_code = models.CharField(max_length=10) # Removed unique=True to match raw DB state

    class Meta:
        db_table = 'home_station'  # Strictly forces Django to use your phpMyAdmin table

    def __str__(self):
        return f"{self.station_name} ({self.station_code})"

class Passenger(models.Model):
    full_name = models.CharField(max_length=100)

    email = models.EmailField(unique=True)

    username = models.CharField(max_length=50, unique=True)

    password = models.CharField(max_length=100)

    aadhaar_number = models.CharField(max_length=12, unique=True)

    phone_number = models.CharField(max_length=15)

    gender = models.CharField(max_length=10)

    address = models.TextField()

    def __str__(self):
        return self.full_name
class LuggageBooking(models.Model):
    passenger = models.ForeignKey(Passenger, on_delete=models.CASCADE)
    source_station = models.ForeignKey(Station, on_delete=models.CASCADE, related_name="source_bookings")
    destination_station = models.ForeignKey(Station, on_delete=models.CASCADE, related_name="destination_bookings")
    
    luggage_type = models.CharField(max_length=100)
    number_of_bags = models.IntegerField()
    weight = models.FloatField()
    travel_date = models.DateField()
    contact_number = models.CharField(max_length=15)
    status = models.CharField(max_length=20, default="Pending")
    created_at = models.DateTimeField(auto_now_add=True)

    # ─── ADD THIS META BLOCK ───
    class Meta:
        db_table = 'home_luggagebooking'

    def __str__(self):
        return self.passenger.full_name