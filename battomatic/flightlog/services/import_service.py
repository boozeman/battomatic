from dataclasses import dataclass, field
from django.db import transaction
from flightlog.models import Flight, FlightSession

from .parser import (
    FlightLogParseError,
    ParsedFlightLog,
    parse_flight_logs,
)
from .preview import (
    DuplicateFlight,
    find_duplicate_flights,
)
from .session_builder import (
    FlightSessionPreview,
    build_flight_sessions,
)

@dataclass(frozen=True)
class ImportError:
    filename: str
    message: str


@dataclass(frozen=True)
class ImportPreview:
    flights: tuple[ParsedFlightLog, ...] = field(default_factory=tuple)
    sessions: tuple[FlightSessionPreview, ...] = field(default_factory=tuple)
    duplicates: tuple[DuplicateFlight, ...] = field(default_factory=tuple)
    errors: tuple[ImportError, ...] = field(default_factory=tuple)

    @property
    def is_valid(self) -> bool:
        return not self.errors and not self.duplicates

    @property
    def flight_count(self) -> int:
        return len(self.flights)

    @property
    def session_count(self) -> int:
        return len(self.sessions)


def build_import_preview(
    *,
    uploaded_files,
    cell_count: int,
    chemistry: str,
) -> ImportPreview:
    flights = []
    errors = []

    for uploaded_file in uploaded_files:
        try:
            flights.extend(
                parse_flight_logs(uploaded_file)
            )
        except FlightLogParseError as error:
            errors.append(
                ImportError(
                    filename=uploaded_file.name,
                    message=str(error),
                )
            )

    duplicates = find_duplicate_flights(flights)

    sessions = []

    if not errors and not duplicates:
        sessions = build_flight_sessions(
            flights,
            cell_count=cell_count,
            chemistry=chemistry,
        )

    return ImportPreview(
        flights=tuple(flights),
        sessions=tuple(sessions),
        duplicates=tuple(duplicates),
        errors=tuple(errors),
    )

@transaction.atomic
def save_import_preview(preview: ImportPreview) -> tuple[FlightSession, ...]:
    if not preview.is_valid:
        raise ValueError("Invalid import preview cannot be saved.")

    created_sessions = []

    for session_preview in preview.sessions:
        session = FlightSession.objects.create(
            aircraft_name=session_preview.model,
            cell_count=session_preview.cell_count,
            chemistry=session_preview.chemistry,
            voltage_threshold=session_preview.voltage_threshold,
        )

        Flight.objects.bulk_create(
            [
                Flight(
                    session=session,
                    start_datetime=flight.start_datetime,
                    end_datetime=flight.end_datetime,
                    flight_time=flight.flight_time,
                    start_voltage=flight.start_voltage,
                    end_voltage=flight.end_voltage,
                    filename=flight.filename,
                )
                for flight in session_preview.flights
            ]
        )

        created_sessions.append(session)

    return tuple(created_sessions)