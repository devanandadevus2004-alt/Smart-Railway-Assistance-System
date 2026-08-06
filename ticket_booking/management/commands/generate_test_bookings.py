from datetime import date

from django.core.management.base import BaseCommand

from ticket_booking.models import (
    Train,
    Coach,
    Seat,
    SeatReservation,
)

from home.models import Station


class Command(BaseCommand):

    help = "Generate booked lower berths for algorithm testing"

    def handle(self, *args, **kwargs):

        TRAIN_NUMBER = "01050"
        COACH_NUMBER = "S1"

        TRAVEL_DATE = date(2026, 8, 6)

        SOURCE_STATION = "Ernakulam Junction"
        DESTINATION_STATION = "Panvel"

        train = Train.objects.get(
            train_number=TRAIN_NUMBER
        )

        coach = Coach.objects.get(
            train=train,
            coach_number=COACH_NUMBER
        )

        source = Station.objects.get(
            station_name=SOURCE_STATION
        )

        destination = Station.objects.get(
            station_name=DESTINATION_STATION
        )

        lower_seats = Seat.objects.filter(
            coach=coach,
            seat_type="LOWER"
        ).order_by("seat_number")

        self.stdout.write(
            self.style.SUCCESS(
                f"Found {lower_seats.count()} lower berths"
            )
        )

        booked = 0

        for seat in lower_seats:

            if seat.seat_number in [61, 66, 71]:
                continue

            exists = SeatReservation.objects.filter(
                seat=seat,
                travel_date=TRAVEL_DATE,
                status="BOOKED"
            ).exists()

            if exists:
                continue

            SeatReservation.objects.create(

                seat=seat,

                travel_date=TRAVEL_DATE,

                source_station=source,

                destination_station=destination,

                status="BOOKED"

            )

            booked += 1

            print(
                f"Booked Lower Berth {seat.seat_number}"
            )

        print()
        print("--------------------------------")
        print(f"Created {booked} bookings")
        print("Remaining Lower Berths:")
        print("61")
        print("66")
        print("71")
        print("--------------------------------")