from dataclasses import dataclass
from datetime import datetime

from ..models import Flight
from .parser import ParsedFlightLog


@dataclass(frozen=True)
class DuplicateFlight:
    filename: str
    start_datetime: datetime
    end_datetime: datetime
    already_imported: bool = False


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

        existing_identities = set(existing_flights)

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