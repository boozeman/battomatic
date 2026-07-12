from django.urls import path

from . import views

app_name = "flightlog"

urlpatterns = [
    path(
        "",
        views.upload_flight_logs,
        name="upload",
    ),
    path(
        "preview/",
        views.preview_flight_logs,
        name="preview",
    ),
]