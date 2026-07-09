from django.contrib import admin
from .models import Battery, ChargeEvent, CellVoltage


class CellVoltageInline(admin.TabularInline):
    model = CellVoltage
    extra = 0


@admin.register(Battery)
class BatteryAdmin(admin.ModelAdmin):
    list_display = ('id', 'state', 'chemistry', 'connector', 'manufacturer', 'model', 'cell_count', 'c_rating', 'capacity_mah', 'purchase_date')
    list_filter = ('state', 'chemistry', 'connector', 'manufacturer')
    search_fields = ('model', 'manufacturer')


@admin.register(ChargeEvent)
class ChargeEventAdmin(admin.ModelAdmin):
    list_display = ('id', 'date', 'battery', 'event')
    list_filter = ('event', 'battery')
    search_fields = ('battery__model', 'notes')
    inlines = [CellVoltageInline]


@admin.register(CellVoltage)
class CellVoltageAdmin(admin.ModelAdmin):
    list_display = ('id', 'event', 'cell_index', 'voltage')
    list_filter = ('event__battery',)
