from django.contrib import messages
from django.shortcuts import redirect, render

from .forms import FlightLogUploadForm
from .services.import_service import build_import_preview
from .services.save_service import persist_import_preview


def upload_flight_logs(request):
    preview = None

    if request.method == "POST":
        form = FlightLogUploadForm(
            request.POST,
            request.FILES,
        )

        if form.is_valid():
            action = request.POST.get(
                "action",
                "preview",
            )

            preview = build_import_preview(
                uploaded_files=form.cleaned_data["files"],
                cell_count=form.cleaned_data["cell_count"],
                chemistry=form.cleaned_data["chemistry"],
            )

            if (
                action == "save"
                and preview.is_valid
            ):
                result = persist_import_preview(
                    preview
                )

                messages.success(
                    request,
                    (
                        f"Successfully imported "
                        f"{result.session_count} battery session(s) "
                        f"containing "
                        f"{result.flight_count} flight(s)."
                    ),
                )

                return redirect(
                    "flightlog:upload",
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
                if preview
                else ()
            ),
            "flight_sessions": (
                preview.sessions
                if preview
                else ()
            ),
            "duplicate_flights": (
                preview.duplicates
                if preview
                else ()
            ),
            "errors": (
                preview.errors
                if preview
                else ()
            ),
        },
    )