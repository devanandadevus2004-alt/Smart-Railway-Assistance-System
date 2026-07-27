from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('ticket_booking', '0003_trainstop'),
    ]

    operations = [
        migrations.SeparateDatabaseAndState(
            database_operations=[],
            state_operations=[
                migrations.AddField(
                    model_name='trainstop',
                    name='station',
                    field=models.ForeignKey(
                        on_delete=models.CASCADE,
                        related_name='train_stops',
                        to='home.station',
                    ),
                ),
                migrations.AddField(
                    model_name='trainstop',
                    name='stop_order',
                    field=models.PositiveIntegerField(),
                ),
                migrations.AddField(
                    model_name='trainstop',
                    name='arrival_time',
                    field=models.TimeField(
                        null=True,
                        blank=True,
                    ),
                ),
                migrations.AddField(
                    model_name='trainstop',
                    name='departure_time',
                    field=models.TimeField(
                        null=True,
                        blank=True,
                    ),
                ),
                migrations.AddField(
                    model_name='train',
                    name='is_reserved',
                    field=models.BooleanField(default=True),
                ),
            ],
        ),
    ]