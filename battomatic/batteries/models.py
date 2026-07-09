from django.core.validators import MinValueValidator, MaxValueValidator
from django.db import models
from django.urls import reverse


class Battery(models.Model):
    class State(models.TextChoices):
        IN_USE = 'IN_USE', 'In Use'
        DECOMMISSIONED = 'DECOMMISSIONED', 'Decommissioned'

    class Chemistry(models.TextChoices):
        LIPO = 'LIPO', 'LiPo'
        LIHV = 'LIHV', 'LiHV'
        LIION = 'LIION', 'Li-Ion'
        LIFE = 'LIFE', 'Li-Fe'
        NICD = 'NICD', 'NiCd'
        NIMH = 'NIMH', 'NiMh'

    class Connector(models.TextChoices):
        XT30 = 'XT30', 'XT-30'
        XT60 = 'XT60', 'XT-60'
        JRFUTABA = 'JR/FUTABA', 'JR/Futaba'

    state = models.CharField(max_length=20, choices=State.choices, default=State.IN_USE)
    chemistry = models.CharField(max_length=20, choices=Chemistry.choices) 
    connector = models.CharField(max_length=10, choices=Connector.choices, default=Connector.XT30)
    purchase_date = models.DateField(null=True, blank=True)
    manufacturer = models.CharField(max_length=120, blank=True)
    model = models.CharField(max_length=120)
    cell_count = models.PositiveSmallIntegerField(validators=[MinValueValidator(1), MaxValueValidator(24)])
    c_rating = models.PositiveSmallIntegerField('C rating', null=True, blank=True)
    capacity_mah = models.PositiveIntegerField('Capacity (mAh)')
    weight_g = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)

    @property
    def health(self):

        charge_events = self.charge_events.prefetch_related("cell_voltages")

        cycles = charge_events.filter(
            event=ChargeEvent.Event.CHARGE
        ).count()

        max_delta = 0

        for event in charge_events:

            values = [
                float(v.voltage)
                for v in event.cell_voltages.all()
                if v.voltage is not None
            ]

            if len(values) < 2:
                continue

            delta = max(values) - min(values)

            if delta > max_delta:
                max_delta = delta

        if max_delta > 0.025:
            return "Needs Attention"

        if cycles > 400:
            return "Aging"

        if max_delta > 0.015:
            return "Fair"

        if cycles > 200:
            return "Good"

        return "Excellent"
        
    class Meta:
        ordering = ['id']

    def __str__(self):
        return f'#{self.id} {self.manufacturer} {self.model}'

    def get_absolute_url(self):
        return reverse('battery_detail', args=[self.pk])

    @property
    def label(self):
        return f'#{self.id} - {self.manufacturer} {self.model} ({self.capacity_mah} mAh)'


class ChargeEvent(models.Model):
    class Event(models.TextChoices):
        CHARGE = 'CHARGE', 'Charge'
        STORAGE = 'STORAGE', 'Storage'
        BALANCE = 'BALANCE', 'Balance'
        DISCHARGE = 'DISCHARGE', 'Discharge'


    date = models.DateField()
    battery = models.ForeignKey(Battery, on_delete=models.CASCADE, related_name='charge_events')
    event = models.CharField(max_length=20, choices=Event.choices)
    charge_current_a = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    notes = models.TextField(blank=True)

    class Meta:
        ordering = ['-date', '-id']

    def __str__(self):
        return f'{self.date} {self.get_event_display()} {self.battery}'

    @property
    def missing_voltage_warning(self):
        charge_count = ChargeEvent.objects.filter(battery=self.battery, event=ChargeEvent.Event.CHARGE).count()
        voltage_count = self.cell_voltages.exclude(voltage__isnull=True).count()
        return charge_count >= 5 and voltage_count == 0


class CellVoltage(models.Model):
    event = models.ForeignKey(ChargeEvent, on_delete=models.CASCADE, related_name='cell_voltages')
    cell_index = models.PositiveSmallIntegerField()
    voltage = models.DecimalField(max_digits=4, decimal_places=3, null=True, blank=True)

    class Meta:
        ordering = ['cell_index']
        unique_together = [('event', 'cell_index')]

    def __str__(self):
        value = self.voltage if self.voltage is not None else 'not recorded'
        return f'{self.event_id} cell {self.cell_index}: {value}'
