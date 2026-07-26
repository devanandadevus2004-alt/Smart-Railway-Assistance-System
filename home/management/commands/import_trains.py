import json
import os
import re

from django.core.management.base import BaseCommand
from django.conf import settings

from home.models import Station
from ticket_booking.models import Train, TrainStop


class Command(BaseCommand):
    help = "Import trains and train stops from EXP-TRAINS.json"

    def handle(self, *args, **kwargs):

        # JSON file location
        json_file = os.path.join(
            settings.BASE_DIR,
            "EXP-TRAINS.json"
        )

        # Check whether file exists
        if not os.path.exists(json_file):
            self.stdout.write(
                self.style.ERROR(
                    f"File not found: {json_file}"
                )
            )
            return

        # Open JSON file
        with open(
            json_file,
            "r",
            encoding="utf-8"
        ) as file:
            data = json.load(file)

        trains_added = 0
        trains_skipped = 0
        stops_added = 0
        stops_skipped = 0

        # Loop through every train
        for train_data in data:

            train_number = train_data.get("trainNumber")
            train_name = train_data.get("trainName")

            train_route = train_data.get(
                "trainRoute",
                []
            )

            # Skip if required information is missing
            if not train_number or not train_name:
                trains_skipped += 1
                continue

            # Remove duplicate train numbers
            if Train.objects.filter(
                train_number=train_number
            ).exists():
                trains_skipped += 1
                continue

            # Need at least two stations
            if len(train_route) < 2:
                trains_skipped += 1
                continue

            # Get first and last station
            first_station_data = train_route[0]
            last_station_data = train_route[-1]

            # Extract station codes
            first_code = extract_station_code(
                first_station_data.get(
                    "stationName",
                    ""
                )
            )

            last_code = extract_station_code(
                last_station_data.get(
                    "stationName",
                    ""
                )
            )

            # Find source and destination stations
            source_station = Station.objects.filter(
                station_code=first_code
            ).first()

            destination_station = Station.objects.filter(
                station_code=last_code
            ).first()

            # Skip if station is not found
            if not source_station or not destination_station:
                trains_skipped += 1
                continue

            # Get departure time
            departure_time = convert_time(
                first_station_data.get(
                    "departs"
                )
            )

            # Get arrival time
            arrival_time = convert_time(
                last_station_data.get(
                    "arrives"
                )
            )

            # Skip if time information is missing
            if not departure_time or not arrival_time:
                trains_skipped += 1
                continue

            # Create Train
            train = Train.objects.create(
                train_number=train_number,
                train_name=train_name,
                source_station=source_station,
                destination_station=destination_station,
                departure_time=departure_time,
                arrival_time=arrival_time,
                is_active=True
            )

            trains_added += 1

            # Create TrainStop records
            for stop in train_route:

                station_name = stop.get(
                    "stationName",
                    ""
                )

                station_code = extract_station_code(
                    station_name
                )

                station = Station.objects.filter(
                    station_code=station_code
                ).first()

                if not station:
                    stops_skipped += 1
                    continue

                arrival = convert_time(
                    stop.get("arrives")
                )

                departure = convert_time(
                    stop.get("departs")
                )

                stop_order = int(
                    stop.get(
                        "sno",
                        0
                    )
                )

                TrainStop.objects.create(
                    train=train,
                    station=station,
                    stop_order=stop_order,
                    arrival_time=arrival,
                    departure_time=departure
                )

                stops_added += 1

        self.stdout.write(
            self.style.SUCCESS(
                "Train import completed successfully!"
            )
        )

        self.stdout.write(
            f"Trains added: {trains_added}"
        )

        self.stdout.write(
            f"Trains skipped: {trains_skipped}"
        )

        self.stdout.write(
            f"Train stops added: {stops_added}"
        )

        self.stdout.write(
            f"Train stops skipped: {stops_skipped}"
        )


def extract_station_code(station_name):
    """
    Extract station code from:
    'MARWAR JN - MJ'

    Returns:
    'MJ'
    """

    if not station_name:
        return None

    match = re.search(
        r"-\s*([A-Z0-9]+)\s*$",
        station_name
    )

    if match:
        return match.group(1)

    return None


def convert_time(time_value):
    """
    Convert dataset time to Django TimeField format.

    Examples:
    '09:45' -> '09:45:00'
    'Source' -> None
    'Destination' -> None
    """

    if not time_value:
        return None

    time_value = str(time_value).strip()

    # Ignore Source / Destination
    if time_value.lower() in [
        "source",
        "destination"
    ]:
        return None

    # Make sure it is a valid HH:MM format
    if re.match(
        r"^\d{1,2}:\d{2}$",
        time_value
    ):
        return time_value

    return None