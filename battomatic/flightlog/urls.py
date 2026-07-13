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
    path(
        "import/",
        views.import_flight_logs,
        name="import",
    ),
    path(
        "sessions/",
        views.session_list,
        name="session-list",
    ),
    path(
        "sessions/<int:pk>/",
        views.session_detail,
        name="session-detail",
    ),
    path(
        "flights/<int:pk>/",
        views.flight_detail,
        name="flight-detail",
    ),

]