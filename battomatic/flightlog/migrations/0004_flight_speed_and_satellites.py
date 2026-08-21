from django.db import migrations, models


FIELDS = (
    (
        "max_speed_kmh",
        models.DecimalField(
            blank=True, decimal_places=1, max_digits=6, null=True
        ),
    ),
    (
        "average_speed_kmh",
        models.DecimalField(
            blank=True, decimal_places=1, max_digits=6, null=True
        ),
    ),
    (
        "max_satellites",
        models.PositiveSmallIntegerField(blank=True, null=True),
    ),
)


def add_missing_columns(apps, schema_editor):
    flight = apps.get_model("flightlog", "Flight")
    connection = schema_editor.connection

    with connection.cursor() as cursor:
        existing_columns = {
            column.name
            for column in connection.introspection.get_table_description(
                cursor,
                flight._meta.db_table,
            )
        }

    for name, field in FIELDS:
        if name in existing_columns:
            continue

        field.set_attributes_from_name(name)
        field.model = flight
        schema_editor.add_field(flight, field)


class Migration(migrations.Migration):
    dependencies = [
        ("flightlog", "0003_flight_gps_metrics"),
    ]

    operations = [
        migrations.SeparateDatabaseAndState(
            database_operations=[
                migrations.RunPython(
                    add_missing_columns,
                    reverse_code=migrations.RunPython.noop,
                ),
            ],
            state_operations=[
                migrations.AddField(
                    model_name="flight",
                    name="max_speed_kmh",
                    field=models.DecimalField(
                        blank=True,
                        decimal_places=1,
                        max_digits=6,
                        null=True,
                    ),
                ),
                migrations.AddField(
                    model_name="flight",
                    name="average_speed_kmh",
                    field=models.DecimalField(
                        blank=True,
                        decimal_places=1,
                        max_digits=6,
                        null=True,
                    ),
                ),
                migrations.AddField(
                    model_name="flight",
                    name="max_satellites",
                    field=models.PositiveSmallIntegerField(
                        blank=True,
                        null=True,
                    ),
                ),
            ],
        ),
    ]
