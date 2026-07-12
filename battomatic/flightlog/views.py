from django.shortcuts import render
from django.views.decorators.http import require_GET, require_POST

from .forms import FlightLogUploadForm
from .services.import_service import build_import_preview


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