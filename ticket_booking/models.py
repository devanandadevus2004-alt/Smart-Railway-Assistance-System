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

    def __str__(self):
        return f"{self.train_number} - {self.train_name}"


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

    seat = models.ForeignKey(
        Seat,
        on_delete=models.CASCADE,
        related_name='ticket_bookings'
    )

    travel_date = models.DateField()

    booking_date = models.DateTimeField(
        auto_now_add=True
    )

    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='CONFIRMED'
    )

    def __str__(self):
        return (
            f"{self.passenger.full_name} - "
            f"{self.train.train_number} - "
            f"{self.seat}"
        )