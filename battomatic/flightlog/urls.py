from django.urls import path

from . import views

app_name = "flightlog"

urlpatterns = [
    path(
        "",
        views.upload_flight_logs,
        name="upload",
    ),
]