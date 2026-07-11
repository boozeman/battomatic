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
    start_reason: str = "first_flight"

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
    def start_voltage(self) -> Decimal:
        return self.flights[0].start_voltage

    @property
    def voltage_threshold(self) -> Decimal:
        return get_new_battery_voltage_threshold(
            cell_count=self.cell_count,
            chemistry=self.chemistry,
        )

    @property
    def start_reason_label(self) -> str:
        labels = {
            "first_flight": "Ensimmäinen löydetty lento",
            "voltage_threshold": "Alkujännite ylitti uuden akun rajan",
            "model_changed": "Mallin nimi vaihtui",
            "date_changed": "Päivämäärä vaihtui",
        }

        return labels.get(
            self.start_reason,
            self.start_reason,
        )

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


def build_flight_sessions(
    flights: list[ParsedFlightLog],
    *,
    cell_count: int,
    chemistry: str,
) -> list[FlightSession]:
    if not flights:
        return []

    threshold = get_new_battery_voltage_threshold(
        cell_count=cell_count,
        chemistry=chemistry,
    )

    ordered_flights = sorted(
        flights,
        key=lambda flight: flight.start_datetime,
    )

    sessions = []
    current_flights = []
    current_start_reason = "first_flight"

    for flight in ordered_flights:
        if not current_flights:
            current_flights.append(flight)
            continue

        previous_flight = current_flights[-1]
        new_session_reason = None

        if flight.date != previous_flight.date:
            new_session_reason = "date_changed"

        elif flight.model != previous_flight.model:
            new_session_reason = "model_changed"

        elif flight.start_voltage >= threshold:
            new_session_reason = "voltage_threshold"

        if new_session_reason is not None:
            sessions.append(
                FlightSession(
                    flights=tuple(current_flights),
                    cell_count=cell_count,
                    chemistry=chemistry,
                    start_reason=current_start_reason,
                )
            )

            current_flights = []
            current_start_reason = new_session_reason

        current_flights.append(flight)

    if current_flights:
        sessions.append(
            FlightSession(
                flights=tuple(current_flights),
                cell_count=cell_count,
                chemistry=chemistry,
                start_reason=current_start_reason,
            )
        )

    return sessions