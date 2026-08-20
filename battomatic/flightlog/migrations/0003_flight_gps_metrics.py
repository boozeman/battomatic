from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("flightlog", "0002_seed_battery_chemistries"),
    ]

    operations = [
        migrations.AddField(
            model_name="flight",
            name="max_altitude_m",
            field=models.DecimalField(
                blank=True, decimal_places=1, max_digits=10, null=True
            ),
        ),
        migrations.AddField(
            model_name="flight",
            name="max_distance_m",
            field=models.DecimalField(
                blank=True, decimal_places=1, max_digits=10, null=True
            ),
        ),
        migrations.AddField(
            model_name="flight",
            name="distance_flown_m",
            field=models.DecimalField(
                blank=True, decimal_places=1, max_digits=10, null=True
            ),
        ),
    ]
