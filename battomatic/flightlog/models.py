import uuid
from datetime import timedelta

from django.db import models
from django.db.models import Max, Min, Sum
from django.utils import timezone


def default_preview_expiry():
    return timezone.now() + timedelta(hours=24)


class FlightImport(models.Model):
    class Status(models.TextChoices):
        PREVIEW = "preview", "Preview"
        COMMITTED = "committed", "Committed"

    public_id = models.UUIDField(
        default=uuid.uuid4,
        unique=True,
        editable=False,
    )

    status = models.CharField(
        max_length=10,
        choices=Status.choices,
        default=Status.PREVIEW,
        db_index=True,
    )

    cell_count = models.PositiveSmallIntegerField()

    chemistry = models.CharField(
        max_length=4,
        choices=[
            ("lipo", "LiPo"),
            ("lihv", "LiHV"),
        ],
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
    )

    updated_at = models.DateTimeField(
        auto_now=True,
    )

    expires_at = models.DateTimeField(
        default=default_preview_expiry,
        db_index=True,
    )

    committed_at = models.DateTimeField(
        null=True,
        blank=True,
    )

    class Meta:
        ordering = [
            "-created_at",
        ]

    def __str__(self):
        return (
            f"{self.public_id} - "
            f"{self.cell_count}S "
            f"{self.get_chemistry_display()} - "
            f"{self.get_status_display()}"
        )

    @property
    def is_preview(self):
        return self.status == self.Status.PREVIEW

    @property
    def is_committed(self):
        return self.status == self.Status.COMMITTED

    @property
    def is_expired(self):
        return (
            self.is_preview
            and self.expires_at <= timezone.now()
        )


class FlightSession(models.Model):
    class Chemistry(models.TextChoices):
        LIPO = "lipo", "LiPo"
        LIHV = "lihv", "LiHV"

    flight_import = models.ForeignKey(
        FlightImport,
        on_delete=models.CASCADE,
        related_name="sessions",
        null=True,
        blank=True,
    )

    aircraft_name = models.CharField(
        max_length=100,
    )

    cell_count = models.PositiveSmallIntegerField()

    chemistry = models.CharField(
        max_length=4,
        choices=Chemistry.choices,
    )

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
            f"{self.get_chemistry_display()}"
        )

    @property
    def first_flight(self):
        return self.flights.order_by(
            "start_datetime"
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