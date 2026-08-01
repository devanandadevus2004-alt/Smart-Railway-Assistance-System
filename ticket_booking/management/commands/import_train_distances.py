import csv
import os

from decimal import Decimal, InvalidOperation

from django.core.management.base import BaseCommand

from ticket_booking.models import (
    Train,
    TrainStopDistance
)

from home.models import Station


class Command(BaseCommand):

    help = (
        'Import train source-to-destination distances '
        'from CSV with resumable batch processing'
    )

    def add_arguments(self, parser):

        parser.add_argument(
            '--file',
            type=str,
            default='Train_details_22122017.csv'
        )

        parser.add_argument(
            '--batch-size',
            type=int,
            default=1000
        )

        parser.add_argument(
            '--reset',
            action='store_true',
            help='Delete existing imported distances and start again'
        )

    def handle(self, *args, **options):

        csv_file = options['file']

        batch_size = options['batch_size']

        reset = options['reset']

        # ====================================================
        # CHECK FILE
        # ====================================================

        if not os.path.exists(csv_file):

            self.stdout.write(
                self.style.ERROR(
                    f'CSV file not found: {csv_file}'
                )
            )

            return

        # ====================================================
        # RESET OPTION
        # ====================================================

        if reset:

            self.stdout.write(
                'Reset option selected.'
            )

            self.stdout.write(
                'Deleting existing distance records...'
            )

            deleted_count, _ = (
                TrainStopDistance.objects.all().delete()
            )

            self.stdout.write(
                self.style.WARNING(
                    f'Deleted {deleted_count} existing records.'
                )
            )

        # ====================================================
        # LOAD EXISTING DATABASE RECORD COUNT
        # ====================================================

        existing_count = (
            TrainStopDistance.objects.count()
        )

        self.stdout.write('')

        self.stdout.write(
            '===== RESUMABLE DISTANCE IMPORT ====='
        )

        self.stdout.write(
            f'Existing distance records: '
            f'{existing_count}'
        )

        self.stdout.write(
            f'Batch size: {batch_size}'
        )

        self.stdout.write('')

        self.stdout.write(
            'Reading CSV dataset...'
        )

        # ====================================================
        # CACHE TRAINS
        # ====================================================

        self.stdout.write(
            'Loading train information...'
        )

        train_cache = {}

        for train in Train.objects.all():

            train_cache[
                train.train_number.strip()
            ] = train.id

        self.stdout.write(
            f'Trains loaded: {len(train_cache)}'
        )

        # ====================================================
        # CACHE STATIONS
        # ====================================================

        self.stdout.write(
            'Loading station information...'
        )

        station_cache = {}

        for station in Station.objects.all():

            station_cache[
                station.station_code.strip().upper()
            ] = station.id

        self.stdout.write(
            f'Stations loaded: {len(station_cache)}'
        )

        # ====================================================
        # COUNTERS
        # ====================================================

        total_rows = 0

        valid_rows = 0

        skipped_rows = 0

        invalid_distances = 0

        unmatched_trains = 0

        unmatched_stations = 0

        processed_batches = 0

        created_records = 0

        updated_records = 0

        # ====================================================
        # ROUTE DATA
        #
        # We process one train + source route at a time.
        #
        # Example:
        #
        # 11003 + DR
        #
        # DR   = 0
        # TNA  = 24
        # PNVL = 61
        # MNI  = 169
        #
        # Then:
        #
        # DR → TNA  = 24
        # DR → PNVL = 61
        # DR → MNI  = 169
        #
        # ====================================================

        current_route_key = None

        current_route_data = {}

        # ====================================================
        # HELPER FUNCTION
        # ====================================================

        def process_route(
            route_key,
            route_data
        ):

            nonlocal created_records

            nonlocal updated_records

            if not route_data:

                return

            train_id = route_key[0]

            source_station_id = route_key[1]

            # -----------------------------------------------
            # Get source cumulative distance
            # -----------------------------------------------

            source_distance = (
                route_data.get(
                    source_station_id
                )
            )

            if source_distance is None:

                source_distance = Decimal(
                    '0'
                )

            # -----------------------------------------------
            # Create source → destination distances
            # -----------------------------------------------

            batch_records = []

            for (
                destination_station_id,
                destination_distance
            ) in route_data.items():

                # -------------------------------------------
                # Skip source → source
                # -------------------------------------------

                if (
                    destination_station_id
                    ==
                    source_station_id
                ):

                    continue

                # -------------------------------------------
                # Calculate journey distance
                # -------------------------------------------

                journey_distance = (
                    destination_distance
                    -
                    source_distance
                )

                # -------------------------------------------
                # Ignore invalid distances
                # -------------------------------------------

                if journey_distance <= 0:

                    continue

                batch_records.append({

                    'train_id':
                        train_id,

                    'source_station_id':
                        source_station_id,

                    'destination_station_id':
                        destination_station_id,

                    'distance':
                        journey_distance

                })

            # -----------------------------------------------
            # Save records
            # -----------------------------------------------

            for record in batch_records:

                (
                    obj,
                    created
                ) = TrainStopDistance.objects.update_or_create(

                    train_id=
                        record[
                            'train_id'
                        ],

                    source_station_id=
                        record[
                            'source_station_id'
                        ],

                    destination_station_id=
                        record[
                            'destination_station_id'
                        ],

                    defaults={

                        'distance':
                            record[
                                'distance'
                            ]

                    }

                )

                if created:

                    created_records += 1

                else:

                    updated_records += 1

        # ====================================================
        # READ CSV
        # ====================================================

        with open(

            csv_file,

            'r',

            encoding='utf-8-sig',

            newline=''

        ) as file:

            reader = csv.DictReader(
                file
            )

            for row in reader:

                total_rows += 1

                # =================================================
                # SHOW PROGRESS
                # =================================================

                if (
                    total_rows % 1000
                    == 0
                ):

                    self.stdout.write(

                        f'Processed CSV rows: '
                        f'{total_rows} | '
                        f'Distance records: '
                        f'{TrainStopDistance.objects.count()}'

                    )

                # =================================================
                # READ CSV VALUES
                # =================================================

                train_number = (

                    row.get(
                        'Train No',
                        ''
                    )
                    .strip()

                )

                station_code = (

                    row.get(
                        'Station Code',
                        ''
                    )
                    .strip()
                    .upper()

                )

                source_code = (

                    row.get(
                        'Source Station',
                        ''
                    )
                    .strip()
                    .upper()

                )

                distance_value = (

                    row.get(
                        'Distance',
                        ''
                    )
                    .strip()

                )

                # =================================================
                # CHECK REQUIRED VALUES
                # =================================================

                if not train_number:

                    skipped_rows += 1

                    continue

                if not station_code:

                    skipped_rows += 1

                    continue

                if not source_code:

                    skipped_rows += 1

                    continue

                # =================================================
                # FIND TRAIN
                # =================================================

                train_id = train_cache.get(
                    train_number
                )

                if not train_id:

                    unmatched_trains += 1

                    continue

                # =================================================
                # FIND SOURCE STATION
                # =================================================

                source_station_id = (
                    station_cache.get(
                        source_code
                    )
                )

                if not source_station_id:

                    unmatched_stations += 1

                    continue

                # =================================================
                # FIND CURRENT STATION
                # =================================================

                current_station_id = (
                    station_cache.get(
                        station_code
                    )
                )

                if not current_station_id:

                    unmatched_stations += 1

                    continue

                # =================================================
                # CONVERT DISTANCE
                # =================================================

                if (

                    not distance_value

                    or

                    distance_value.upper()
                    == 'NA'

                ):

                    invalid_distances += 1

                    continue

                try:

                    distance = Decimal(
                        distance_value
                    )

                except (
                    InvalidOperation,
                    ValueError,
                    TypeError
                ):

                    invalid_distances += 1

                    continue

                # =================================================
                # ROUTE KEY
                # =================================================

                route_key = (

                    train_id,

                    source_station_id

                )

                # =================================================
                # DETECT NEW ROUTE
                # =================================================

                if (

                    current_route_key
                    is not None

                    and

                    route_key
                    !=
                    current_route_key

                ):

                    # ---------------------------------------------
                    # Process completed route
                    # ---------------------------------------------

                    process_route(

                        current_route_key,

                        current_route_data

                    )

                    processed_batches += 1

                    # ---------------------------------------------
                    # Clear previous route
                    # ---------------------------------------------

                    current_route_data = {}

                # =================================================
                # SET CURRENT ROUTE
                # =================================================

                current_route_key = (
                    route_key
                )

                # =================================================
                # STORE DISTANCE
                # =================================================

                current_route_data[
                    current_station_id
                ] = distance

                valid_rows += 1

        # ====================================================
        # PROCESS FINAL ROUTE
        # ====================================================

        if (

            current_route_key
            is not None

            and

            current_route_data

        ):

            process_route(

                current_route_key,

                current_route_data

            )

            processed_batches += 1

        # ====================================================
        # FINAL RESULT
        # ====================================================

        final_count = (
            TrainStopDistance.objects.count()
        )

        self.stdout.write('')

        self.stdout.write(

            self.style.SUCCESS(

                '===== IMPORT COMPLETED ====='

            )

        )

        self.stdout.write(

            f'Total CSV rows: '
            f'{total_rows}'

        )

        self.stdout.write(

            f'Valid CSV rows: '
            f'{valid_rows}'

        )

        self.stdout.write(

            f'Skipped rows: '
            f'{skipped_rows}'

        )

        self.stdout.write(

            f'Invalid/NA distances: '
            f'{invalid_distances}'

        )

        self.stdout.write(

            f'Unmatched trains: '
            f'{unmatched_trains}'

        )

        self.stdout.write(

            f'Unmatched stations: '
            f'{unmatched_stations}'

        )

        self.stdout.write(

            f'Processed routes: '
            f'{processed_batches}'

        )

        self.stdout.write(

            f'New records: '
            f'{created_records}'

        )

        self.stdout.write(

            f'Updated records: '
            f'{updated_records}'

        )

        self.stdout.write(

            f'Total distance records in database: '
            f'{final_count}'

        )

        self.stdout.write('')

        self.stdout.write(

            self.style.SUCCESS(

                'Distance import finished successfully.'

            )

        )