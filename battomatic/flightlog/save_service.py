from dataclasses import dataclass

from django.db import transaction

from .import_service import ImportPreview
from .models import Flight, FlightSession


class ImportSaveError(ValueError):
    """Raised when an import preview cannot be saved."""


@dataclass(frozen=True)
class SavedImportResult:
    session_ids: tuple[int, ...]
    session_count: int
    flight_count: int


@transaction.atomic
def save_import_preview(
    preview: ImportPreview,
) -> SavedImportResult:
    if not preview.is_valid:
        raise ImportSaveError(
            "Only a valid import preview can be saved."
        )

    created_sessions = []
    created_flight_count = 0

    for session_preview in preview.sessions:
        session = FlightSession.objects.create(
            aircraft_name=session_preview.model,
            cell_count=session_preview.cell_count,
            chemistry=session_preview.chemistry,
            voltage_threshold=session_preview.voltage_threshold,
        )

        created_sessions.append(session)

        for flight_preview in session_preview.flights:
            Flight.objects.create(
                session=session,
                start_datetime=flight_preview.start_datetime,
                end_datetime=flight_preview.end_datetime,
                flight_time=flight_preview.flight_time,
                start_voltage=flight_preview.start_voltage,
                end_voltage=flight_preview.end_voltage,
                filename=flight_preview.filename,
            )

            created_flight_count += 1

    return SavedImportResult(
        session_ids=tuple(
            session.pk
            for session in created_sessions
        ),
        session_count=len(created_sessions),
        flight_count=created_flight_count,
    )