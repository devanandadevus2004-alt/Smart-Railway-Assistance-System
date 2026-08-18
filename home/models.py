from django.db import models
from ticket_booking.models import TicketBooking


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

    transfer_type = models.CharField(
    max_length=20,
    choices=[
        ('WITH_TICKET', 'Passenger Luggage - With Ticket'),
        ('WITHOUT_TICKET', 'Parcel / Unaccompanied Transfer - Without Passenger Ticket'),
    ],
        default='WITH_TICKET'
    )

    ticket_booking = models.ForeignKey(
    'ticket_booking.TicketBooking',
    on_delete=models.SET_NULL,
    null=True,
    blank=True,
    related_name='luggage_bookings'
)
    source_station = models.ForeignKey(Station, on_delete=models.CASCADE, related_name="source_bookings")
    destination_station = models.ForeignKey(Station, on_delete=models.CASCADE, related_name="destination_bookings")
    
    luggage_type = models.CharField(max_length=100)
    number_of_bags = models.IntegerField()
    weight = models.FloatField()
    travel_date = models.DateField()
    contact_number = models.CharField(max_length=15)
    status = models.CharField(
    max_length=30,
    default="Pending"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    verification_date = models.DateField(null=True, blank=True)

    verification_time = models.TimeField(null=True, blank=True)

    instructions = models.TextField(blank=True)
    rejection_reason = models.TextField(blank=True)

    

    # ─── ADD THIS META BLOCK ───
    class Meta:
        db_table = 'home_luggagebooking'

    def __str__(self):
        return self.passenger.full_name
class Officer(models.Model):
    full_name = models.CharField(max_length=100)

    employee_id = models.CharField(max_length=20, unique=True)

    username = models.CharField(max_length=50, unique=True)

    password = models.CharField(max_length=100)

    email = models.EmailField(unique=True)

    phone_number = models.CharField(max_length=10)

    station = models.ForeignKey(Station, on_delete=models.CASCADE)

    designation = models.CharField(max_length=50, default="Parcel Officer")

    def __str__(self):
        return f"{self.full_name} - {self.station.station_name}"

class Hospital(models.Model):

    station = models.ForeignKey(
        Station,
        on_delete=models.CASCADE,
        related_name="hospitals"
    )

    hospital_name = models.CharField(
        max_length=200
    )

    address = models.TextField()

    contact_number = models.CharField(
        max_length=15
    )

    distance_km = models.DecimalField(
        max_digits=4,
        decimal_places=1
    )

    def __str__(self):
        return (
            f"{self.hospital_name} - "
            f"{self.station.station_name}"
        )


class LuggageItem(models.Model):

    booking = models.ForeignKey(
        LuggageBooking,
        on_delete=models.CASCADE,
        related_name="items"
    )

    item_number = models.PositiveIntegerField()

    luggage_type = models.CharField(
        max_length=100
    )

    weight = models.FloatField()

    def __str__(self):
        return (
            f"Item {self.item_number} - "
            f"{self.luggage_type} - "
            f"{self.weight} kg"
        )