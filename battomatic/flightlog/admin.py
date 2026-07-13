from django.contrib import admin

from .models import BatteryChemistry, Flight, FlightSession


@admin.register(BatteryChemistry)
class BatteryChemistryAdmin(admin.ModelAdmin):
    list_display = (
        "name",
        "slug",
        "session_start_voltage_per_cell",
        "is_active",
        "sort_order",
    )
    list_editable = (
        "session_start_voltage_per_cell",
        "is_active",
        "sort_order",
    )
    list_filter = (
        "is_active",
    )
    search_fields = (
        "name",
        "slug",
    )
    ordering = (
        "sort_order",
        "name",
    )
    prepopulated_fields = {
        "slug": (
            "name",
        ),
    }


@admin.register(FlightSession)
class FlightSessionAdmin(admin.ModelAdmin):
    list_display = (
        "aircraft_name",
        "date",
        "cell_count",
        "chemistry",
        "voltage_threshold",
        "flight_count",
        "created_at",
    )
    list_filter = (
        "chemistry",
        "cell_count",
    )
    search_fields = (
        "aircraft_name",
    )
    readonly_fields = (
        "created_at",
    )


@admin.register(Flight)
class FlightAdmin(admin.ModelAdmin):
    list_display = (
        "session",
        "start_datetime",
        "flight_time",
        "start_voltage",
        "end_voltage",
        "filename",
    )
    list_filter = (
        "session__chemistry",
        "session__cell_count",
    )
    search_fields = (
        "session__aircraft_name",
        "filename",
    )