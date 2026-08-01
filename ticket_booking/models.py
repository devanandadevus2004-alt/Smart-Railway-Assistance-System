from django.db import models


class Train(models.Model):
    train_number = models.CharField(max_length=20, unique=True)
    train_name = models.CharField(max_length=100)

    source_station = models.ForeignKey(
        'home.Station',
        on_delete=models.CASCADE,
        related_name='trains_from'
    )

    destination_station = models.ForeignKey(
        'home.Station',
        on_delete=models.CASCADE,
        related_name='trains_to'
    )

    departure_time = models.TimeField()
    arrival_time = models.TimeField()

    is_active = models.BooleanField(default=True)
    is_reserved = models.BooleanField(default=True)

    def __str__(self):
        return f"{self.train_number} - {self.train_name}"


class TrainStop(models.Model):

    train = models.ForeignKey(  
    Train,  
    on_delete=models.CASCADE,  
    related_name='stops'  
    )  

    station = models.ForeignKey(  
    'home.Station',  
    on_delete=models.CASCADE,  
    related_name='train_stops'  
    )  

    stop_order = models.PositiveIntegerField()  

    arrival_time = models.TimeField(  
    null=True,  
    blank=True  
    )  

    departure_time = models.TimeField(  
    null=True,  
    blank=True  
    )  




    class Meta:  
        ordering = ['stop_order']  
        unique_together = ('train', 'station')  

    def __str__(self):  
        return (  
            f"{self.train.train_number} - "  
            f"{self.stop_order} - "  
            f"{self.station.station_name}"  
        )


class TrainStopDistance(models.Model):

    train = models.ForeignKey(
        Train,
        on_delete=models.CASCADE,
        related_name='stop_distances'
    )

    source_station = models.ForeignKey(
        'home.Station',
        on_delete=models.CASCADE,
        related_name='distance_sources'
    )

    destination_station = models.ForeignKey(
        'home.Station',
        on_delete=models.CASCADE,
        related_name='distance_destinations'
    )

    distance = models.DecimalField(
        max_digits=10,
        decimal_places=2
    )

    class Meta:

        unique_together = (
            'train',
            'source_station',
            'destination_station'
        )

        ordering = [
            'train',
            'source_station',
            'destination_station'
        ]

    def __str__(self):

        return (
            f"{self.train.train_number} - "
            f"{self.source_station.station_code} → "
            f"{self.destination_station.station_code} - "
            f"{self.distance} km"
        )


class Coach(models.Model):

    COACH_TYPE_CHOICES = [
        ('GEN','General / Unreserved'),
        ('SL', 'Sleeper'),
        ('3A', 'AC 3 Tier'),
        ('2A', 'AC 2 Tier'),
        ('1A', 'AC First Class'),
        ('CC', 'Chair Car'),
        ('EC', 'Executive Chair Car'),
    ]

    train = models.ForeignKey(
        Train,
        on_delete=models.CASCADE,
        related_name='coaches'
    )

    coach_number = models.CharField(max_length=10)

    coach_type = models.CharField(
        max_length=5,
        choices=COACH_TYPE_CHOICES
    )

    total_seats = models.PositiveIntegerField(default=0)

    is_bookable = models.BooleanField(default=True)

    has_seat_layout = models.BooleanField(default=True)

    def __str__(self):
        return f"{self.train.train_number} - {self.coach_number}"


class Seat(models.Model):

    SEAT_TYPE_CHOICES = [
        ('LOWER', 'Lower Berth'),
        ('MIDDLE', 'Middle Berth'),
        ('UPPER', 'Upper Berth'),
        ('SIDE_LOWER', 'Side Lower Berth'),
        ('SIDE_UPPER', 'Side Upper Berth'),
        ('WINDOW', 'Window Seat'),
        ('MIDDLE_SEAT', 'Middle Seat'),
        ('AISLE', 'Aisle Seat'),
    ]

    coach = models.ForeignKey(
        Coach,
        on_delete=models.CASCADE,
        related_name='seats'
    )

    seat_number = models.PositiveIntegerField()

    seat_type = models.CharField(
        max_length=20,
        choices=SEAT_TYPE_CHOICES
    )

    row_number = models.PositiveIntegerField(default=1)

    position = models.CharField(
        max_length=20,
        blank=True
    )

    is_active = models.BooleanField(default=True)

    def __str__(self):
        return f"{self.coach.coach_number} - Seat {self.seat_number}"


class TicketBooking(models.Model):

    STATUS_CHOICES = [
        ('PENDING', 'Pending'),
        ('CONFIRMED', 'Confirmed'),
        ('CANCELLED', 'Cancelled'),
    ]

    passenger = models.ForeignKey(
        'home.Passenger',
        on_delete=models.CASCADE,
        related_name='ticket_bookings'
    )

    train = models.ForeignKey(
        Train,
        on_delete=models.CASCADE,
        related_name='ticket_bookings'
    )

    travel_date = models.DateField()

    fare = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0
    )

    booking_date = models.DateTimeField(
        auto_now_add=True
    )

    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='PENDING'
    )

    def __str__(self):
        return (
            f"{self.passenger.full_name} - "
            f"{self.train.train_number} - "
            f"Booking {self.id}"
        )

class BookingPassenger(models.Model):

    GENDER_CHOICES = [
        ('MALE', 'Male'),
        ('FEMALE', 'Female'),
        ('OTHER', 'Other'),
    ]

    booking = models.ForeignKey(
        TicketBooking,
        on_delete=models.CASCADE,
        related_name='booking_passengers'
    )

    full_name = models.CharField(
        max_length=100
    )

    age = models.PositiveIntegerField()

    gender = models.CharField(
        max_length=10,
        choices=GENDER_CHOICES
    )

    aadhaar_number = models.CharField(
        max_length=12
    )

    seat = models.ForeignKey(
        Seat,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='booking_passengers'
    )

    fare = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0
    )

    def __str__(self):

        return (
            f"{self.full_name} - "
            f"{self.booking.train.train_number}"
        )

class Payment(models.Model):

    PAYMENT_METHOD_CHOICES = [
        ('UPI', 'UPI'),
        ('CARD', 'Credit / Debit Card'),
        ('NET_BANKING', 'Net Banking'),
    ]

    PAYMENT_STATUS_CHOICES = [
        ('PENDING', 'Pending'),
        ('SUCCESS', 'Success'),
        ('FAILED', 'Failed'),
        ('REFUNDED', 'Refunded'),
    ]

    booking = models.OneToOneField(
        TicketBooking,
        on_delete=models.CASCADE,
        related_name='payment'
    )

    amount = models.DecimalField(
        max_digits=10,
        decimal_places=2
    )

    payment_method = models.CharField(
        max_length=20,
        choices=PAYMENT_METHOD_CHOICES
    )

    payment_status = models.CharField(
        max_length=20,
        choices=PAYMENT_STATUS_CHOICES,
        default='PENDING'
    )

    transaction_id = models.CharField(
        max_length=100,
        unique=True,
        null=True,
        blank=True
    )

    paid_at = models.DateTimeField(
        null=True,
        blank=True
    )

    def __str__(self):
        return (
            f"Payment - "
            f"{self.booking.passenger.full_name} - "
            f"{self.payment_status}"
        )


class SeatReservation(models.Model):

    STATUS_CHOICES = [
        ('LOCKED', 'Temporarily Locked'),
        ('BOOKED', 'Booked'),
        ('CANCELLED', 'Cancelled'),
        ('EXPIRED', 'Expired'),
    ]

    seat = models.ForeignKey(
        Seat,
        on_delete=models.CASCADE,
        related_name='reservations'
    )

    booking = models.ForeignKey(
        TicketBooking,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='seat_reservations'
    )

    travel_date = models.DateField()

    source_station = models.ForeignKey(
        'home.Station',
        on_delete=models.CASCADE,
        related_name='seat_reservation_sources'
    )

    destination_station = models.ForeignKey(
        'home.Station',
        on_delete=models.CASCADE,
        related_name='seat_reservation_destinations'
    )

    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='LOCKED'
    )

    locked_at = models.DateTimeField(
        null=True,
        blank=True
    )

    lock_expires_at = models.DateTimeField(
        null=True,
        blank=True
    )

    reserved_at = models.DateTimeField(
        auto_now_add=True
    )

    def __str__(self):
        return (
            f"{self.seat.coach.train.train_number} - "
            f"{self.seat.coach.coach_number} - "
            f"Seat {self.seat.seat_number} - "
            f"{self.travel_date} - "
            f"{self.status}"
        )
