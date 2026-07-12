from dataclasses import dataclass
from datetime import datetime
from .parser import ParsedFlightLog
from .services.parser import ParsedFlightLog


@dataclass(frozen=True)
class DuplicateFlight:
    filename: str
    start_datetime: datetime
    end_datetime: datetime


def find_duplicate_flights(
    flights: list[ParsedFlightLog],
) -> list[DuplicateFlight]:
    seen = set()
    duplicates = []

    for flight in flights:
        identity = (
            flight.filename,
            flight.start_datetime,
            flight.end_datetime,
        )

        if identity in seen:
            duplicates.append(
                DuplicateFlight(
                    filename=flight.filename,
                    start_datetime=flight.start_datetime,
                    end_datetime=flight.end_datetime,
                )
            )
        else:
            seen.add(identity)

    return duplicates