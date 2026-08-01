from django.core.management.base import BaseCommand

from ticket_booking.models import TrainStopDistance


class Command(BaseCommand):

    help = (
        'Verify imported train source-to-destination '
        'distance records'
    )

    def handle(self, *args, **options):

        # ====================================================
        # TOTAL RECORDS
        # ====================================================

        total_records = (
            TrainStopDistance.objects.count()
        )

        self.stdout.write('')

        self.stdout.write(
            '===== IMPORTED DISTANCE VERIFICATION ====='
        )

        self.stdout.write(
            f'Total distance records: '
            f'{total_records}'
        )

        # ====================================================
        # INVALID DISTANCES
        # ====================================================

        invalid_records = (
            TrainStopDistance.objects.filter(
                distance__lte=0
            ).count()
        )

        self.stdout.write(
            f'Invalid distances (0 or negative): '
            f'{invalid_records}'
        )

        # ====================================================
        # SAMPLE RECORDS
        # ====================================================

        self.stdout.write('')

        self.stdout.write(
            '===== SAMPLE IMPORTED DISTANCES ====='
        )

        samples = (
            TrainStopDistance.objects
            .select_related(
                'train',
                'source_station',
                'destination_station'
            )
            .order_by(
                'train__train_number',
                'source_station__station_code',
                'destination_station__station_code'
            )[:20]
        )

        for record in samples:

            self.stdout.write(

                f'Train: '
                f'{record.train.train_number} | '

                f'{record.source_station.station_code} '
                f'-> '
                f'{record.destination_station.station_code} | '

                f'Distance: '
                f'{record.distance} km'

            )

        # ====================================================
        # SPECIFIC TRAIN CHECK
        # ====================================================

        self.stdout.write('')

        self.stdout.write(
            '===== SAMPLE TRAIN 11003 ====='
        )

        train_records = (
            TrainStopDistance.objects
            .filter(
                train__train_number='11003'
            )
            .select_related(
                'train',
                'source_station',
                'destination_station'
            )
            .order_by(
                'distance'
            )[:20]
        )

        if not train_records.exists():

            self.stdout.write(
                'No distance records found for '
                'Train 11003.'
            )

        else:

            for record in train_records:

                self.stdout.write(

                    f'{record.source_station.station_code} '
                    f'-> '
                    f'{record.destination_station.station_code} '
                    f'= '
                    f'{record.distance} km'

                )

        # ====================================================
        # FINAL RESULT
        # ====================================================

        self.stdout.write('')

        if invalid_records == 0:

            self.stdout.write(

                self.style.SUCCESS(

                    'All imported distance records '
                    'have valid positive distances.'

                )

            )

        else:

            self.stdout.write(

                self.style.WARNING(

                    f'{invalid_records} records have '
                    f'invalid distances.'

                )

            )

        self.stdout.write('')

        self.stdout.write(

            self.style.SUCCESS(

                'Distance verification completed.'

            )

        )