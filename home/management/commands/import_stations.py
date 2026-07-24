import json
from django.core.management.base import BaseCommand
from home.models import Station


class Command(BaseCommand):
    help = "Import railway stations from railwayStationsList.json"

    def handle(self, *args, **kwargs):

        file_path = "railwayStationsList.json"

        try:
            with open(file_path, "r", encoding="utf-8") as file:
                data = json.load(file)

        except FileNotFoundError:
            self.stdout.write(
                self.style.ERROR(
                    "railwayStationsList.json not found."
                )
            )
            return

        # Get station list from JSON
        if isinstance(data, dict):

            # If JSON contains a key that stores the station list
            stations = None

            for value in data.values():
                if isinstance(value, list):
                    stations = value
                    break

            if stations is None:
                self.stdout.write(
                    self.style.ERROR(
                        "Could not find station list in JSON file."
                    )
                )
                return

        elif isinstance(data, list):
            stations = data

        else:
            self.stdout.write(
                self.style.ERROR(
                    "Invalid JSON format."
                )
            )
            return

        added = 0
        skipped = 0

        for station in stations:

            station_code = station.get("stnCode")
            station_name = station.get("stnName")

            if not station_code or not station_name:
                skipped += 1
                continue

            station_code = station_code.strip()
            station_name = station_name.strip()

            # Check if station already exists
            if Station.objects.filter(
                station_code=station_code
            ).exists():

                skipped += 1
                continue

            # Add new station
            Station.objects.create(
                station_code=station_code,
                station_name=station_name
            )

            added += 1

        self.stdout.write(
            self.style.SUCCESS(
                "Station import completed successfully!"
            )
        )

        self.stdout.write(
            f"Stations added: {added}"
        )

        self.stdout.write(
            f"Stations skipped: {skipped}"
        )