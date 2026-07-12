from django.shortcuts import render

from .services.forms import FlightLogUploadForm
from .services.import_service import build_import_preview


def upload_flight_logs(request):
    preview = None

    if request.method == "POST":
        form = FlightLogUploadForm(
            request.POST,
            request.FILES,
        )

        if form.is_valid():
            preview = build_import_preview(
                uploaded_files=form.cleaned_data["files"],
                cell_count=form.cleaned_data["cell_count"],
                chemistry=form.cleaned_data["chemistry"],
            )
    else:
        form = FlightLogUploadForm()

    return render(
        request,
        "flightlog/upload.html",
        {
            "form": form,
            "preview": preview,
            "parsed_logs": (
                preview.flights
                if preview is not None
                else []
            ),
            "flight_sessions": (
                preview.sessions
                if preview is not None
                else []
            ),
            "duplicate_flights": (
                preview.duplicates
                if preview is not None
                else []
            ),
            "errors": (
                preview.errors
                if preview is not None
                else []
            ),
        },
    )