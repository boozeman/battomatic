from django import forms
from django.forms import inlineformset_factory

from .models import Battery, ChargeEvent, CellVoltage


class BatteryChoiceField(forms.ModelChoiceField):
    def label_from_instance(self, obj):
        return obj.label


class ChargeEventForm(forms.ModelForm):
    class Meta:
        model = ChargeEvent
        fields = [
            "date",
            "battery",
            "event",
            "charge_current_a",
            "notes",
        ]
        widgets = {
            "date": forms.DateInput(
                attrs={
                    "type": "date",
                    "class": "form-control",
                }
            ),
            "battery": forms.Select(
                attrs={
                    "class": "form-control",
                }
            ),
            "event": forms.Select(
                attrs={
                    "class": "form-control",
                }
            ),
            "charge_current_a": forms.NumberInput(
                attrs={
                    "class": "form-control",
                    "step": "0.01",
                    "placeholder": "5.00",
                }
            ),
            "notes": forms.Textarea(
                attrs={
                    "class": "form-control",
                    "rows": 3,
                }
            ),
        }

    def __init__(self, *args, battery=None, **kwargs):
        super().__init__(*args, **kwargs)

        selected_battery = battery

        if selected_battery is None:
            battery_id = (
                self.data.get("battery")
                or self.initial.get("battery")
            )

            if battery_id:
                try:
                    selected_battery = Battery.objects.get(pk=battery_id)
                except Battery.DoesNotExist:
                    selected_battery = None

        if selected_battery is None and self.instance and self.instance.pk:
            selected_battery = self.instance.battery

        self.selected_battery = selected_battery
        self.cell_voltage_fields = []

        if not selected_battery:
            return

        # Charge current placeholder:
        # 1C based on capacity, rounded down to nearest 0.1 A.
        # Example: 850 mAh -> 0.8 A, 5000 mAh -> 5.0 A
        charge_current_placeholder = (
            selected_battery.capacity_mah // 100
        ) / 10

        self.fields["charge_current_a"].widget.attrs["placeholder"] = (
            f"{charge_current_placeholder:.1f}"
        )

        # Cell voltage placeholder based on chemistry.
        cell_voltage_placeholder = {
            "LIPO": "4.200",
            "LIHV": "4.350",
            "LIFE": "3.600",
            "LIION": "3.600",
        }.get(selected_battery.chemistry, "4.200")

        for i in range(1, selected_battery.cell_count + 1):
            field_name = f"cell_{i}"

            initial_voltage = None

            if self.instance and self.instance.pk:
                existing = self.instance.cell_voltages.filter(
                    cell_index=i
                ).first()

                if existing:
                    initial_voltage = existing.voltage

            self.fields[field_name] = forms.DecimalField(
                label=f"Cell {i}",
                required=False,
                max_digits=4,
                decimal_places=3,
                initial=initial_voltage,
                widget=forms.NumberInput(
                    attrs={
                        "class": "form-control",
                        "step": "0.001",
                        "placeholder": cell_voltage_placeholder,
                    }
                ),
            )

            self.cell_voltage_fields.append(self[field_name])

    def save(self, commit=True):
        charge_event = super().save(commit=commit)

        if commit and self.selected_battery:
            charge_event.cell_voltages.filter(
                cell_index__gt=self.selected_battery.cell_count
            ).delete()

            for i in range(1, self.selected_battery.cell_count + 1):
                field_name = f"cell_{i}"
                voltage = self.cleaned_data.get(field_name)

                CellVoltage.objects.update_or_create(
                    event=charge_event,
                    cell_index=i,
                    defaults={
                        "voltage": voltage,
                    },
                )

        return charge_event


class CellVoltageForm(forms.ModelForm):
    class Meta:
        model = CellVoltage
        fields = ["cell_index", "voltage"]
        widgets = {
            "cell_index": forms.NumberInput(
                attrs={
                    "readonly": "readonly",
                }
            ),
            "voltage": forms.NumberInput(
                attrs={
                    "step": "0.001",
                    "min": "0",
                    "max": "9.999",
                    "placeholder": "e.g. 4.200",
                }
            ),
        }


CellVoltageFormSet = inlineformset_factory(
    ChargeEvent,
    CellVoltage,
    form=CellVoltageForm,
    fields=("cell_index", "voltage"),
    extra=0,
    can_delete=False,
)
