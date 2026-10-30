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
        BT20 = 'BT2.0', 'BT2.0'
        PH20 = 'PH2.0', 'PH2.0'
        XT30 = 'XT30', 'XT-30'
        XT60 = 'XT60', 'XT-60'
        XT90 = 'XT90', 'XT-90'
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

        # Classify the largest measured cell voltage difference (in volts).
        if max_delta <= 0.010:  # 0–10 mV
            return "Excellent"
        if max_delta <= 0.020:  # 10–20 mV
            return "Very good"
        if max_delta <= 0.030:  # 20–30 mV
            return "Good / normal"
        if max_delta <= 0.050:  # 30–50 mV
            return "Consider balancing and monitoring"
        if max_delta <= 0.100:  # 50–100 mV
            return "Clearly unbalanced"
        return "Concerning — inspect battery and individual cells"
        
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
