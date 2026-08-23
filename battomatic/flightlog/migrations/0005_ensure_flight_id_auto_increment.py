from django.db import migrations


def ensure_flight_id_auto_increment(apps, schema_editor):
    """Repair databases created with a non-auto-increment Flight ID."""
    if schema_editor.connection.vendor != "mysql":
        return

    flight = apps.get_model("flightlog", "Flight")
    table_name = schema_editor.quote_name(flight._meta.db_table)
    column_name = schema_editor.quote_name("id")

    with schema_editor.connection.cursor() as cursor:
        cursor.execute(
            f"SHOW COLUMNS FROM {table_name} LIKE %s",
            ["id"],
        )
        column = cursor.fetchone()

        if column is None or "auto_increment" in column[5].lower():
            return

        column_type = column[1]
        cursor.execute(
            f"ALTER TABLE {table_name} MODIFY COLUMN {column_name} "
            f"{column_type} NOT NULL AUTO_INCREMENT"
        )


class Migration(migrations.Migration):
    dependencies = [
        ("flightlog", "0004_flight_speed_and_satellites"),
    ]

    operations = [
        migrations.RunPython(
            ensure_flight_id_auto_increment,
            reverse_code=migrations.RunPython.noop,
        ),
    ]
