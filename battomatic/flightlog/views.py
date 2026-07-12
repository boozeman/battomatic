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
    form = FlightLogUploadForm(
        request.POST,
        request.FILES,
    )

    form_is_valid = form.is_valid()
    preview = None

    if form_is_valid:
        preview = build_import_preview(
            uploaded_files=form.cleaned_data["files"],
            cell_count=form.cleaned_data["cell_count"],
            chemistry=form.cleaned_data["chemistry"],
        )

    context = {
        "form": form,
        "preview": preview,
        "parsed_logs": preview.flights if preview else (),
        "flight_sessions": preview.sessions if preview else (),
        "duplicate_flights": preview.duplicates if preview else (),
        "errors": preview.errors if preview else (),
    }

    return render(
        request,
        "flightlog/_preview.html",
        context,
        status=200 if form_is_valid else 400,
    )