from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("flightlog", "0003_flight_gps_metrics"),
    ]

    operations = [
        migrations.AddField(
            model_name="flight",
            name="max_speed_kmh",
            field=models.DecimalField(
                blank=True, decimal_places=1, max_digits=6, null=True
            ),
        ),
        migrations.AddField(
            model_name="flight",
            name="average_speed_kmh",
            field=models.DecimalField(
                blank=True, decimal_places=1, max_digits=6, null=True
            ),
        ),
        migrations.AddField(
            model_name="flight",
            name="max_satellites",
            field=models.PositiveSmallIntegerField(blank=True, null=True),
        ),
    ]
