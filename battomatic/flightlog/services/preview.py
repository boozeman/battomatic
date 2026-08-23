from dataclasses import dataclass
from datetime import datetime

from django.utils import timezone

from ..models import Flight
from .parser import ParsedFlightLog


@dataclass(frozen=True)
class DuplicateFlight:
    filename: str
    start_datetime: datetime
    end_datetime: datetime
    already_imported: bool = False


def _database_datetime(value: datetime) -> datetime:
    """Convert a CSV timestamp as Django does before writing it to the DB."""
    if timezone.is_naive(value):
        return timezone.make_aware(value)

    return value


def find_duplicate_flights(
    flights: list[ParsedFlightLog],
) -> list[DuplicateFlight]:
    seen = set()
    duplicates = []

    identities = {
        (
            flight.filename,
            flight.start_datetime,
            flight.end_datetime,
        )
        for flight in flights
    }

    existing_identities = set()

    if identities:
        for filename, start_datetime, end_datetime in identities:
            if Flight.objects.filter(
                filename=filename,
                start_datetime=_database_datetime(start_datetime),
                end_datetime=_database_datetime(end_datetime),
            ).exists():
                existing_identities.add(
                    (filename, start_datetime, end_datetime)
                )

    for flight in flights:
        identity = (
            flight.filename,
            flight.start_datetime,
            flight.end_datetime,
        )

        if identity in existing_identities:
            duplicates.append(
                DuplicateFlight(
                    filename=flight.filename,
                    start_datetime=flight.start_datetime,
                    end_datetime=flight.end_datetime,
                    already_imported=True,
                )
            )
            continue

        if identity in seen:
            duplicates.append(
                DuplicateFlight(
                    filename=flight.filename,
                    start_datetime=flight.start_datetime,
                    end_datetime=flight.end_datetime,
                    already_imported=False,
                )
            )
            continue

        seen.add(identity)

    return duplicates
