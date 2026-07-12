from django.shortcuts import render

from .forms import FlightLogUploadForm
from .parser import FlightLogParseError, parse_flight_logs
from .preview import find_duplicate_flights
from .session_builder import build_flight_sessions


def upload_flight_logs(request):
    parsed_logs = []
    flight_sessions = []
    duplicate_flights = []
    errors = []

    if request.method == "POST":
        form = FlightLogUploadForm(
            request.POST,
            request.FILES,
        )

        if form.is_valid():
            for uploaded_file in form.cleaned_data["files"]:
                try:
                    parsed_logs.extend(
                        parse_flight_logs(uploaded_file)
                    )
                except FlightLogParseError as error:
                    errors.append(
                        {
                            "filename": uploaded_file.name,
                            "message": str(error),
                        }
                    )

            duplicate_flights = find_duplicate_flights(
                parsed_logs
            )

            if not duplicate_flights:
                flight_sessions = build_flight_sessions(
                    parsed_logs,
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
            "parsed_logs": parsed_logs,
            "flight_sessions": flight_sessions,
            "duplicate_flights": duplicate_flights,
            "errors": errors,
        },
    )