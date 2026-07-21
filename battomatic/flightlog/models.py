from datetime import timedelta

from django.db import models
from django.db.models import Max, Min, Sum


class BatteryChemistry(models.Model):
    name = models.CharField(
        max_length=50,
        unique=True,
    )
    slug = models.SlugField(
        max_length=50,
        unique=True,
    )
    session_start_voltage_per_cell = models.DecimalField(
        max_digits=4,
        decimal_places=2,
        help_text=(
            "Per-cell voltage at or above which a new "
            "battery session is started."
        ),
    )
    is_active = models.BooleanField(
        default=True,
        help_text=(
            "Inactive chemistries are hidden from the "
            "flight log upload form."
        ),
    )
    sort_order = models.PositiveSmallIntegerField(
        default=0,
    )

    class Meta:
        ordering = [
            "sort_order",
            "name",
        ]
        verbose_name = "Battery chemistry"
        verbose_name_plural = "Battery chemistries"

    def __str__(self):
        return self.name


class FlightSession(models.Model):
    aircraft_name = models.CharField(
        max_length=100,
    )
    cell_count = models.PositiveSmallIntegerField()

    # Snapshot of the chemistry used during import.
    chemistry = models.CharField(
        max_length=50,
    )

    # Snapshot of the complete battery threshold used during import.
    voltage_threshold = models.DecimalField(
        max_digits=5,
        decimal_places=2,
    )
    created_at = models.DateTimeField(
        auto_now_add=True,
    )

    class Meta:
        ordering = [
            "-created_at",
            "aircraft_name",
        ]

    def __str__(self):
        return (
            f"{self.aircraft_name} - "
            f"{self.cell_count}S "
            f"{self.chemistry}"
        )

    @property
    def first_flight(self):
        return self.flights.order_by(
            "start_datetime",
        ).first()

    @property
    def date(self):
        first_flight = self.first_flight

        if first_flight is None:
            return None

        return first_flight.start_datetime.date()

    @property
    def start_voltage(self):
        first_flight = self.first_flight

        if first_flight is None:
            return None

        return first_flight.start_voltage

    @property
    def end_voltage(self):
        last_flight = self.flights.order_by(
            "-end_datetime",
        ).first()

        if last_flight is None:
            return None

        return last_flight.end_voltage

    @property
    def flight_count(self):
        return self.flights.count()

    @property
    def total_flight_time(self):
        result = self.flights.aggregate(
            total=Sum("flight_time"),
        )

        return result["total"] or timedelta()

    @property
    def longest_flight_time(self):
        result = self.flights.aggregate(
            longest=Max("flight_time"),
        )

        return result["longest"]

    @property
    def shortest_flight_time(self):
        result = self.flights.aggregate(
            shortest=Min("flight_time"),
        )

        return result["shortest"]


class Flight(models.Model):
    session = models.ForeignKey(
        FlightSession,
        on_delete=models.CASCADE,
        related_name="flights",
    )
    start_datetime = models.DateTimeField()
    end_datetime = models.DateTimeField()
    flight_time = models.DurationField()
    start_voltage = models.DecimalField(
        max_digits=5,
        decimal_places=2,
    )
    end_voltage = models.DecimalField(
        max_digits=5,
        decimal_places=2,
    )
    filename = models.CharField(
        max_length=255,
    )

    class Meta:
        ordering = [
            "start_datetime",
        ]
        constraints = [
            models.UniqueConstraint(
                fields=[
                    "filename",
                    "start_datetime",
                    "end_datetime",
                ],
                name="unique_imported_flight",
            ),
        ]

    def __str__(self):
        return (
            f"{self.session.aircraft_name} - "
            f"{self.start_datetime:%Y-%m-%d %H:%M:%S}"
        )
