from django.contrib import messages
from django.shortcuts import get_object_or_404, render
from django.views.decorators.http import require_GET, require_POST

from .forms import FlightLogUploadForm
from .models import Flight, FlightSession
from .services.import_service import (
    build_import_preview,
    save_import_preview,
)

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
        "flights",
    ).all()

    return render(
        request,
        "flightlog/session_list.html",
        {
            "sessions": sessions,
        },
    )


@require_GET
def session_detail(request, pk):
    session = get_object_or_404(
        FlightSession.objects.prefetch_related("flights"),
        pk=pk,
    )

    return render(
        request,
        "flightlog/session_detail.html",
        {
            "session": session,
            "flights": session.flights.all(),
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
    form = FlightLogUploadForm(request.POST, request.FILES)

    if not form.is_valid():
        return render(
            request,
            "flightlog/_preview.html",
            _preview_context(form=form),
            status=400,
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
            _preview_context(form=form, preview=preview),
            status=400,
        )

    created_sessions = save_import_preview(preview)

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