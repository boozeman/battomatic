from django.shortcuts import render

from .forms import FlightLogUploadForm
from .parser import FlightLogParseError, parse_flight_logs


def upload_flight_logs(request):
    parsed_logs = []
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
    else:
        form = FlightLogUploadForm()

    return render(
        request,
        "flightlog/upload.html",
        {
            "form": form,
            "parsed_logs": parsed_logs,
            "errors": errors,
        },
    )