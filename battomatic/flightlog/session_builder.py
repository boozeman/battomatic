from dataclasses import dataclass
from datetime import timedelta
from decimal import Decimal

from .parser import ParsedFlightLog, format_duration


NEW_BATTERY_CELL_VOLTAGE = {
    "lipo": Decimal("4.00"),
    "lihv": Decimal("4.25"),
}


class FlightSessionBuildError(ValueError):
    """Raised when flight sessions cannot be built."""


@dataclass(frozen=True)
class FlightSession:
    flights: tuple[ParsedFlightLog, ...]
    cell_count: int
    chemistry: str

    @property
    def date(self):
        return self.flights[0].date

    @property
    def model(self):
        return self.flights[0].model

    @property
    def session_count(self):
        return len(self.flights)

    @property
    def total_flight_time(self) -> timedelta:
        return sum(
            (flight.flight_time for flight in self.flights),
            start=timedelta(),
        )

    @property
    def longest_flight_time(self) -> timedelta:
        return max(
            flight.flight_time
            for flight in self.flights
        )

    @property
    def shortest_flight_time(self) -> timedelta:
        return min(
            flight.flight_time
            for flight in self.flights
        )

    @property
    def formatted_total_flight_time(self) -> str:
        return format_duration(self.total_flight_time)

    @property
    def formatted_longest_flight_time(self) -> str:
        return format_duration(self.longest_flight_time)

    @property
    def formatted_shortest_flight_time(self) -> str:
        return format_duration(self.shortest_flight_time)


def get_new_battery_voltage_threshold(
    cell_count: int,
    chemistry: str,
) -> Decimal:
    if cell_count < 1:
        raise FlightSessionBuildError(
            "Kennomäärän pitää olla vähintään yksi."
        )

    try:
        per_cell_voltage = NEW_BATTERY_CELL_VOLTAGE[chemistry]
    except KeyError as error:
        raise FlightSessionBuildError(
            f"Tuntematon akkukemia: {chemistry}"
        ) from error

    return per_cell_voltage * cell_count