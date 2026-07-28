from django.core.management.base import BaseCommand

from ticket_booking.models import Train, Coach, Seat


class Command(BaseCommand):

    help = "Create or resume coaches and seats for imported trains"

    def handle(self, *args, **kwargs):

        trains = Train.objects.all()

        coaches_created = 0
        seats_created = 0
        trains_completed = 0

        for train in trains:

            # --------------------------------
            # DEFINE COACH LIST
            # --------------------------------

            if train.is_active:

                coach_list = [

                    {
                        "number": "GEN-1",
                        "type": "GEN",
                        "bookable": False,
                        "seats": 0
                    },

                    {
                        "number": "S1",
                        "type": "SL",
                        "bookable": True,
                        "seats": 72
                    },

                    {
                        "number": "S2",
                        "type": "SL",
                        "bookable": True,
                        "seats": 72
                    },

                    {
                        "number": "S3",
                        "type": "SL",
                        "bookable": True,
                        "seats": 72
                    },

                    {
                        "number": "B1",
                        "type": "3A",
                        "bookable": True,
                        "seats": 64
                    },

                    {
                        "number": "B2",
                        "type": "3A",
                        "bookable": True,
                        "seats": 64
                    },

                    {
                        "number": "A1",
                        "type": "2A",
                        "bookable": True,
                        "seats": 48
                    },

                    {
                        "number": "GEN-2",
                        "type": "GEN",
                        "bookable": False,
                        "seats": 0
                    },
                ]

            else:

                coach_list = [

                    {
                        "number": "GEN-1",
                        "type": "GEN",
                        "bookable": False,
                        "seats": 0
                    },

                    {
                        "number": "GEN-2",
                        "type": "GEN",
                        "bookable": False,
                        "seats": 0
                    },
                ]


            # --------------------------------
            # PROCESS EACH COACH
            # --------------------------------

            for coach_data in coach_list:

                # Check whether this coach already exists
                coach = Coach.objects.filter(
                    train=train,
                    coach_number=coach_data["number"]
                ).first()


                # --------------------------------
                # CREATE MISSING COACH
                # --------------------------------

                if not coach:

                    coach = Coach.objects.create(

                        train=train,

                        coach_number=coach_data[
                            "number"
                        ],

                        coach_type=coach_data[
                            "type"
                        ],

                        total_seats=coach_data[
                            "seats"
                        ],

                        is_bookable=coach_data[
                            "bookable"
                        ],

                        has_seat_layout=coach_data[
                            "bookable"
                        ]
                    )

                    coaches_created += 1

                    self.stdout.write(
                        f"Created coach "
                        f"{coach.coach_number} "
                        f"for train "
                        f"{train.train_number}"
                    )


                # --------------------------------
                # CREATE MISSING SEATS
                # --------------------------------

                if coach_data["bookable"]:

                    seat_types = [
                        "LOWER",
                        "MIDDLE",
                        "UPPER",
                        "SIDE_LOWER",
                        "SIDE_UPPER"
                    ]

                    for seat_number in range(
                        1,
                        coach_data["seats"] + 1
                    ):

                        # Check whether seat already exists
                        seat_exists = Seat.objects.filter(
                            coach=coach,
                            seat_number=seat_number
                        ).exists()

                        if seat_exists:
                            continue


                        seat_type = seat_types[
                            (seat_number - 1)
                            % len(seat_types)
                        ]


                        Seat.objects.create(

                            coach=coach,

                            seat_number=seat_number,

                            seat_type=seat_type,

                            row_number=(
                                (seat_number - 1)
                                // 6
                            ) + 1,

                            position=""
                        )

                        seats_created += 1


            trains_completed += 1


        # --------------------------------
        # FINAL OUTPUT
        # --------------------------------

        self.stdout.write("")

        self.stdout.write(
            self.style.SUCCESS(
                "Coach generation/resume completed!"
            )
        )

        self.stdout.write(
            f"Trains processed: "
            f"{trains_completed}"
        )

        self.stdout.write(
            f"Coaches created: "
            f"{coaches_created}"
        )

        self.stdout.write(
            f"Seats created: "
            f"{seats_created}"
        )