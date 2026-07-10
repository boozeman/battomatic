import qrcode
from io import BytesIO
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfgen import canvas
from reportlab.lib.utils import ImageReader
from django.utils import timezone
from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models import Count
from django.http import JsonResponse, HttpResponse
from django.shortcuts import redirect, get_object_or_404
from django.urls import reverse, reverse_lazy
from django.views.generic import CreateView, DetailView, ListView, TemplateView, UpdateView
from .forms import BatteryForm, ChargeEventForm
from .models import Battery, CellVoltage, ChargeEvent

# Date sorting
def get_sort(request, allowed, default):
    sort = request.GET.get("sort", default)

    if sort not in allowed:
        return default

    return sort

class BatteryListView(ListView):
    model = Battery
    template_name = 'batteries/battery_list.html'
    context_object_name = 'batteries'

    def get_queryset(self):
        qs = Battery.objects.annotate(event_count=Count('charge_events'))
        battery_id = self.request.GET.get('battery')
        if battery_id:
            qs = qs.filter(pk=battery_id)
        return qs

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['all_batteries'] = Battery.objects.all()
        ctx['selected_battery'] = self.request.GET.get('battery', '')
        return ctx
class BatteryCreateView(LoginRequiredMixin, CreateView):
    model = Battery
    form_class = BatteryForm
    template_name = "batteries/battery_form.html"
    success_url = reverse_lazy("battery_list")

class BatteryDetailView(DetailView):
    model = Battery
    template_name = "batteries/battery_detail.html"
    context_object_name = "battery"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        battery = self.object

        sort = get_sort(
            self.request,
            allowed={"date", "-date"},
            default="-date",
        )

        events = (
            ChargeEvent.objects
            .filter(battery=battery)
            .prefetch_related("cell_voltages")
            .order_by(sort, "-id")
        )

        context["events"] = events
        context["sort"] = sort

        context["charge_cycle_count"] = events.filter(
            event=ChargeEvent.Event.CHARGE
        ).count()

        context["storage_count"] = events.filter(
            event=ChargeEvent.Event.STORAGE
        ).count()

        context["balance_count"] = events.filter(
            event=ChargeEvent.Event.BALANCE
        ).count()

        context["discharge_count"] = events.filter(
            event=ChargeEvent.Event.DISCHARGE
        ).count()

        context["last_charge"] = events.filter(
            event=ChargeEvent.Event.CHARGE
        ).order_by("-date", "-id").first()

        context["last_storage"] = events.filter(
            event=ChargeEvent.Event.STORAGE
        ).order_by("-date", "-id").first()

        chart_events = []

        for event in events:
            voltages = list(event.cell_voltages.all())

            values = [
                float(v.voltage)
                for v in voltages
                if v.voltage is not None
            ]

            if not values:
                continue

            row = {
                "date": event.date.strftime("%Y-%m-%d"),
                "event": event.event,
                "event_id": event.id,
            }

            for voltage in voltages:
                if voltage.voltage is not None:
                    key = f"cell_{voltage.cell_index}"
                    row[key] = float(voltage.voltage)

            if len(values) >= 2:
                row["delta"] = round(max(values) - min(values), 3)
            else:
                row["delta"] = None

            chart_events.append(row)

        context["chart_events"] = chart_events

        return context

class BatteryUpdateView(LoginRequiredMixin, UpdateView):
    model = Battery
    form_class = BatteryForm
    template_name = "batteries/battery_form.html"

    def get_success_url(self):
        return reverse(
            "battery_detail",
            args=[self.object.pk],
        )

class BatteryQuickChargeView(LoginRequiredMixin, CreateView):
    model = ChargeEvent
    form_class = ChargeEventForm
    template_name = "batteries/quick_charge.html"

    def dispatch(self, request, *args, **kwargs):
        self.battery = Battery.objects.get(pk=self.kwargs["pk"])
        return super().dispatch(request, *args, **kwargs)

    def get_initial(self):
        initial = super().get_initial()

        initial["battery"] = self.battery
        initial["event"] = ChargeEvent.Event.CHARGE
        initial["date"] = timezone.localdate()

        return initial

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["battery"] = self.battery
        return context

    def form_valid(self, form):
        form.instance.battery = self.battery
        return super().form_valid(form)

    def get_success_url(self):
        return reverse(
            "battery_detail",
            args=[self.battery.pk],
        )

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["battery"] = self.battery
        return kwargs

class ChargeEventListView(ListView):
    model = ChargeEvent
    template_name = "batteries/charge_event_list.html"
    context_object_name = "events"
    paginate_by = 50

    def get_queryset(self):
        sort = get_sort(
            self.request,
            allowed={"date", "-date"},
            default="-date",
        )

        qs = (
            ChargeEvent.objects
            .select_related("battery")
            .prefetch_related("cell_voltages")
            .order_by(sort, "-id")
        )

        battery_id = self.request.GET.get("battery")
        if battery_id:
            qs = qs.filter(battery_id=battery_id)

        return qs

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)

        ctx["sort"] = get_sort(
            self.request,
            allowed={"date", "-date"},
            default="-date",
        )

        ctx["all_batteries"] = Battery.objects.all()
        ctx["selected_battery"] = self.request.GET.get("battery", "")

        return ctx

class ChargeEventMixin(LoginRequiredMixin):
    model = ChargeEvent
    form_class = ChargeEventForm
    template_name = "batteries/charge_event_form.html"
    success_url = reverse_lazy("charge_event_list")

    def dispatch(self, request, *args, **kwargs):
        if not Battery.objects.exists():
            messages.warning(
                request,
                "Add at least one battery in Django Admin before creating charge events."
            )
            return redirect("battery_list")

        return super().dispatch(request, *args, **kwargs)

    def get_initial(self):
        initial = super().get_initial()

        battery_id = self.request.GET.get("battery")
        if battery_id:
            initial["battery"] = battery_id

        if not self.object:
            initial.setdefault("date", timezone.localdate())

        return initial

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()

        battery = None

        if self.request.method == "GET":
            battery_id = self.request.GET.get("battery")

            if battery_id:
                battery = Battery.objects.filter(pk=battery_id).first()

        if battery is None and getattr(self, "object", None):
            battery = self.object.battery

        if battery is not None:
            kwargs["battery"] = battery

        return kwargs

    def form_valid(self, form):
        self.object = form.save()
        self.warn_if_needed(self.object)
        return redirect(self.get_success_url())

    def warn_if_needed(self, event):
        charge_count = ChargeEvent.objects.filter(
            battery=event.battery,
            event=ChargeEvent.Event.CHARGE,
        ).count()

        any_voltages = event.cell_voltages.exclude(
            voltage__isnull=True
        ).exists()

        if charge_count >= 5 and not any_voltages:
            messages.warning(
                self.request,
                f"{event.battery.label} has at least five charge events. "
                "Consider recording cell voltages.",
            )


class ChargeEventCreateView(ChargeEventMixin, CreateView):
    pass


class ChargeEventUpdateView(ChargeEventMixin, UpdateView):
    pass


class VoltageChartView(TemplateView):
    template_name = "batteries/voltage_chart.html"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)

        battery_id = self.request.GET.get("battery")
        selected_event = self.request.GET.get("event", "all")

        batteries = Battery.objects.all().order_by("id")

        selected_battery = (
            batteries.filter(pk=battery_id).first()
            if battery_id
            else batteries.first()
        )

        chart_events = []

        if selected_battery:
            events = (
                selected_battery.charge_events
                .prefetch_related("cell_voltages")
                .order_by("date", "id")
            )

            for event in events:
                voltages = list(event.cell_voltages.all())

                values = [
                    float(v.voltage)
                    for v in voltages
                    if v.voltage is not None
                ]

                if not values:
                    continue

                row = {
                    "date": event.date.strftime("%Y-%m-%d"),
                    "event": event.event,
                    "event_id": event.id,
                }

                for voltage in voltages:
                    if voltage.voltage is not None:
                        row[f"cell_{voltage.cell_index}"] = float(voltage.voltage)

                row["delta"] = (
                    round(max(values) - min(values), 3)
                    if len(values) >= 2
                    else None
                )

                chart_events.append(row)

        ctx.update({
            "all_batteries": batteries,
            "selected_battery": selected_battery,
            "selected_event": selected_event,
            "chart_events": chart_events,
        })

        return ctx

# Battery api

def battery_api(request, pk):
    battery = Battery.objects.get(pk=pk)
    return JsonResponse({'id': battery.id, 'model': battery.model, 'capacity_mah': battery.capacity_mah, 'cell_count': battery.cell_count})

# Battery QR-Code

def battery_qr_code(request, pk):
    battery = get_object_or_404(Battery, pk=pk)

    url = request.build_absolute_uri(
        reverse("battery_quick_charge", args=[battery.pk])
    )

    qr = qrcode.QRCode(version=1, box_size=10, border=2,)

    qr.add_data(url)
    qr.make(fit=True)

    img = qr.make_image(fill_color="black", back_color="white")

    buffer = BytesIO()
    img.save(buffer,format="PNG")

    return HttpResponse(
        buffer.getvalue(),
        content_type="image/png",
    )

# Battery labels to PDF

def battery_label_pdf(request, pk):
    battery = get_object_or_404(Battery, pk=pk)

    response = HttpResponse(content_type="application/pdf")
    response["content-Disposition"] = (f'inline; filename="battery_{battery.id}_label.pdf"')

    # Label size

    width = 40 * mm
    height = 24 * mm

    pdf = canvas.Canvas(response, pagesize=(width, height))

    # QR Code

    qr_url = request.build_absolute_uri(
        reverse("battery_quick_charge", args=[battery.pk])
    )

    qr = qrcode.QRCode(version=1, box_size=10, border=2)
    qr.add_data(qr_url)
    qr.make(fit=True)

    qr_img = qr.make_image(fill_color="black", background="white")

    qr_buffer = BytesIO()
    qr_img.save(qr_buffer, format="PNG")
    qr_buffer.seek(0)

    qr_size = 20 * mm
    qr_x = 12 * mm
    qr_y = 2 * mm


    # Battery Number

    pdf.saveState()
    pdf.rotate(90)
    pdf.setFont("Helvetica-Bold",18)
    pdf.drawString(10 * mm, -6 * mm, f"{battery.id}")
    pdf.restoreState()

    # Purchace date

    pdf.saveState()
    pdf.rotate(90)
    pdf.setFont("Helvetica", 7)
    pdf.drawString(6 * mm, -10 * mm,f"{battery.purchase_date}")
    pdf.restoreState()

    # Draw the QR-code

    pdf.drawImage(ImageReader(qr_buffer), qr_x, qr_y, width=qr_size, height=qr_size, preserveAspectRatio=True, mask="auto")

    # Footer

    pdf.saveState()
    pdf.rotate(90)
    pdf.setFont("Helvetica", 7)
    pdf.drawString(6 * mm,-35 * mm,"Batt-o-Matic")
    pdf.restoreState()

    pdf.showPage()
    pdf.save()

    return response
