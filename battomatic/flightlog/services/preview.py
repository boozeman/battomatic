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


def _local_naive_datetime(value: datetime) -> datetime:
    """Use the CSV's local timestamp when comparing imported flights.

    Parsed CSV timestamps are naive local datetimes. Django returns database
    datetimes as aware UTC values when ``USE_TZ`` is enabled, so comparing the
    two directly makes an already imported flight look new until the database
    unique constraint rejects it during saving.
    """
    if timezone.is_aware(value):
        return timezone.make_naive(value)

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
        filenames = {
            filename
            for filename, _, _ in identities
        }

        existing_flights = (
            Flight.objects
            .filter(filename__in=filenames)
            .values_list(
                "filename",
                "start_datetime",
                "end_datetime",
            )
        )

        existing_identities = {
            (
                filename,
                _local_naive_datetime(start_datetime),
                _local_naive_datetime(end_datetime),
            )
            for filename, start_datetime, end_datetime in existing_flights
        }

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
