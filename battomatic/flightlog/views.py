from collections import OrderedDict
from dataclasses import dataclass, field
from datetime import date as date_type, timedelta

from django.contrib import messages
from django.db.models import Prefetch
from django.shortcuts import get_object_or_404, render
from django.views.decorators.http import require_GET, require_POST
from django.db import IntegrityError

from .forms import FlightLogUploadForm
from .models import Flight, FlightSession
from .services.import_service import (
    build_import_preview,
    save_import_preview,
)


@dataclass
class SessionListItem:
    session: FlightSession
    start_datetime: object
    flight_count: int
    total_flight_time: timedelta
    start_voltage: object = None
    end_voltage: object = None


@dataclass
class FlightDayGroup:
    date: object
    aircraft_name: str
    sessions: list[SessionListItem] = field(default_factory=list)
    flight_count: int = 0
    total_flight_time: timedelta = field(default_factory=timedelta)


@dataclass
class SessionDetailSummary:
    date: object
    flight_count: int
    total_flight_time: timedelta
    longest_flight_time: timedelta | None
    start_voltage: object = None
    end_voltage: object = None
    total_distance_m: object = None
    max_speed_kmh: object = None
    max_altitude_m: object = None
    max_satellites: int | None = None


def _maximum_present(flights, attribute):
    values = [
        getattr(flight, attribute)
        for flight in flights
        if getattr(flight, attribute) is not None
    ]
    return max(values) if values else None

def _preview_context(*, form, preview=None):
    return {
        "form": form,
        "preview": preview,
        "parsed_logs": preview.flights if preview else (),
        "flight_sessions": preview.sessions if preview else (),
        "duplicate_flights": preview.duplicates if preview else (),
        "errors": preview.errors if preview else (),
    }

@require_GET
def session_list(request):
    sessions = FlightSession.objects.prefetch_related(
        Prefetch(
            "flights",
            queryset=Flight.objects.order_by("start_datetime"),
        ),
    )
    groups_by_key = OrderedDict()

    for session in sessions:
        flights = list(session.flights.all())
        date = flights[0].start_datetime.date() if flights else None
        key = (date, session.aircraft_name)
        group = groups_by_key.get(key)

        if group is None:
            group = FlightDayGroup(
                date=date,
                aircraft_name=session.aircraft_name,
            )
            groups_by_key[key] = group

        total_flight_time = sum(
            (flight.flight_time for flight in flights),
            start=timedelta(),
        )
        item = SessionListItem(
            session=session,
            start_datetime=(flights[0].start_datetime if flights else None),
            flight_count=len(flights),
            total_flight_time=total_flight_time,
            start_voltage=flights[0].start_voltage if flights else None,
            end_voltage=flights[-1].end_voltage if flights else None,
        )
        group.sessions.append(item)
        group.flight_count += item.flight_count
        group.total_flight_time += item.total_flight_time

    groups = list(groups_by_key.values())
    for group in groups:
        group.sessions.sort(
            key=lambda item: item.start_datetime or date_type.min,
        )
    groups.sort(key=lambda group: group.aircraft_name.casefold())
    groups.sort(key=lambda group: group.date or date_type.min, reverse=True)

    return render(
        request,
        "flightlog/session_list.html",
        {
            "session_groups": groups,
        },
    )


@require_GET
def session_detail(request, pk):
    session = get_object_or_404(
        FlightSession.objects.prefetch_related("flights"),
        pk=pk,
    )

    flights = list(session.flights.all())
    distances = [
        flight.distance_flown_m
        for flight in flights
        if flight.distance_flown_m is not None
    ]
    summary = SessionDetailSummary(
        date=flights[0].start_datetime.date() if flights else None,
        flight_count=len(flights),
        total_flight_time=sum(
            (flight.flight_time for flight in flights),
            start=timedelta(),
        ),
        longest_flight_time=(
            max(flight.flight_time for flight in flights)
            if flights
            else None
        ),
        start_voltage=flights[0].start_voltage if flights else None,
        end_voltage=flights[-1].end_voltage if flights else None,
        total_distance_m=sum(distances) if distances else None,
        max_speed_kmh=_maximum_present(flights, "max_speed_kmh"),
        max_altitude_m=_maximum_present(flights, "max_altitude_m"),
        max_satellites=_maximum_present(flights, "max_satellites"),
    )

    return render(
        request,
        "flightlog/session_detail.html",
        {
            "session": session,
            "flights": flights,
            "summary": summary,
        },
    )


@require_GET
def flight_detail(request, pk):
    flight = get_object_or_404(
        Flight.objects.select_related("session"),
        pk=pk,
    )

    return render(
        request,
        "flightlog/flight_detail.html",
        {
            "flight": flight,
        },
    )

@require_GET
def upload_flight_logs(request):
    form = FlightLogUploadForm()

    return render(
        request,
        "flightlog/upload.html",
        {
            "form": form,
            "preview": None,
            "parsed_logs": (),
            "flight_sessions": (),
            "duplicate_flights": (),
            "errors": (),
        },
    )


@require_POST
def preview_flight_logs(request):
    form = FlightLogUploadForm(request.POST, request.FILES)

    if not form.is_valid():
        context = {
            "form": form,
            "preview": None,
            "parsed_logs": (),
            "flight_sessions": (),
            "duplicate_flights": (),
            "errors": (),
        }
        return render(
            request,
            "flightlog/_preview.html",
            context,
            status=400,
        )

    preview = build_import_preview(
        uploaded_files=form.cleaned_data["files"],
        cell_count=form.cleaned_data["cell_count"],
        chemistry=form.cleaned_data["chemistry"],
    )

    context = {
        "form": form,
        "preview": preview,
        "parsed_logs": preview.flights,
        "flight_sessions": preview.sessions,
        "duplicate_flights": preview.duplicates,
        "errors": preview.errors,
    }

    return render(
        request,
        "flightlog/_preview.html",
        context,
        status=200,
    )

@require_POST
def import_flight_logs(request):
    form = FlightLogUploadForm(
        request.POST,
        request.FILES,
    )

    if not form.is_valid():
        return render(
            request,
            "flightlog/_preview.html",
            _preview_context(form=form),
        )

    preview = build_import_preview(
        uploaded_files=form.cleaned_data["files"],
        cell_count=form.cleaned_data["cell_count"],
        chemistry=form.cleaned_data["chemistry"],
    )

    if not preview.is_valid:
        return render(
            request,
            "flightlog/_preview.html",
            _preview_context(
                form=form,
                preview=preview,
            ),
        )

    try:
        created_sessions = save_import_preview(preview)
    except IntegrityError:
        form.add_error(
            None,
            (
                "One or more flight logs have already been imported. "
                "No flight logs were saved."
            ),
        )

        return render(
            request,
            "flightlog/_preview.html",
            _preview_context(
                form=form,
                preview=None,
            ),
        )

    return render(
        request,
        "flightlog/_import_result.html",
        {
            "created_sessions": created_sessions,
            "created_session_count": len(created_sessions),
            "created_flight_count": preview.flight_count,
        },
        status=201,
    )
