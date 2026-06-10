from datetime import datetime

from ajax_datatable import AjaxDatatableView
from django.contrib import messages
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse, reverse_lazy
from django.views import View
from django.views.generic import DetailView, TemplateView

from src.buildings.models import Flats, Floors, Houses, Sections
from src.core.mixins import RoleRequiredMixin
from src.finances.forms import MeterReadingForm
from src.finances.models import MeterReadings


def parse_filter_date(value):
    value = (value or "").strip()
    if not value:
        return None
    for fmt in ("%d.%m.%Y", "%Y-%m-%d"):
        try:
            return datetime.strptime(value, fmt).date()
        except ValueError:
            continue
    return None


def selected_object(model, value):
    if not value:
        return None
    try:
        return model.objects.get(pk=value)
    except (model.DoesNotExist, TypeError, ValueError):
        return None


def get_sections(request):
    house_id = request.GET.get("house_id")

    sections = Sections.objects.filter(house_id=house_id).values("id", "title")

    return JsonResponse(list(sections), safe=False)


def get_floors(request):
    house_id = request.GET.get("house_id")

    floors = Floors.objects.filter(house_id=house_id).values("id", "title")

    return JsonResponse(list(floors), safe=False)


def get_flats(request):
    house_id = request.GET.get("house_id")
    section_id = request.GET.get("section_id")
    floor_id = request.GET.get("floor_id")

    flats = Flats.objects.filter(
        house_id=house_id, section_id=section_id, floor_id=floor_id
    ).values("id", "number")

    return JsonResponse(list(flats), safe=False)


class MeterReadingsListView(RoleRequiredMixin, TemplateView):
    permission_required = "has_meter_readings"
    template_name = "meter_readings/list.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["page_title"] = "Liczniki"
        context["breadcrumbs"] = [
            {
                "title": "Liczniki",
                "url": reverse_lazy("finances:meter_readings_list"),
            },
        ]
        return context


class MeterReadingsAjaxDatatableView(RoleRequiredMixin, AjaxDatatableView):
    permission_required = "has_meter_readings"
    model = MeterReadings
    title = "Liczniki"
    initial_order = [["created_at", "desc"]]
    length_menu = [[10, 25, 50], [10, 25, 50]]
    disable_queryset_optimization = True

    column_defs = [
        {"name": "house", "title": "Budynek"},
        {"name": "section", "title": "Sekcja"},
        {"name": "flat", "title": "Nr mieszkania"},
        {"name": "meter_type", "title": "Licznik"},
        {"name": "current_data", "title": "Bieżące odczyty"},
        {"name": "unit", "title": "Jedn. miary"},
        {"name": "actions", "title": ""},
    ]

    def get_initial_queryset(self, request=None):
        queryset = MeterReadings.objects.select_related(
            "flat",
            "flat__house",
            "flat__section",
            "flat__floor",
            "meter_type",
            "meter_type__unit_of_measurement",
        )

        if request is None:
            return queryset

        house = request.GET.get("house", "").strip()
        section = request.GET.get("section", "").strip()
        flat_number = request.GET.get("flat_number", "").strip()
        meter_type = request.GET.get("meter_type", "").strip()
        flat_id = request.GET.get("flat_id", "").strip()

        if flat_id.isdigit():
            queryset = queryset.filter(flat_id=int(flat_id))
        else:
            if house:
                queryset = queryset.filter(flat__house__title__icontains=house)
            if section:
                queryset = queryset.filter(
                    flat__section__title__icontains=section
                )
            if flat_number:
                if flat_number.isdigit():
                    queryset = queryset.filter(flat__number=int(flat_number))
                else:
                    queryset = queryset.none()
        if meter_type:
            queryset = queryset.filter(meter_type__title__icontains=meter_type)

        return queryset

    def render_column(self, row, column):

        if column == "house":
            return (
                row.flat.house.title
                if row.flat_id and row.flat.house_id
                else "-"
            )

        if column == "section":
            return (
                row.flat.section.title
                if row.flat_id and row.flat.section_id
                else "-"
            )

        if column == "flat":
            return row.flat.number if row.flat_id else "-"

        if column == "meter_type":
            return row.meter_type.title if row.meter_type_id else "-"

        if column == "unit":
            unit = (
                row.meter_type.unit_of_measurement
                if row.meter_type_id
                else None
            )
            return unit.title if unit else "-"

        if column == "actions":
            update_url = reverse(
                "finances:meter_readings_update", args=[row.pk]
            )
            delete_url = reverse(
                "finances:meter_readings_delete", args=[row.pk]
            )
            csrf = self.request.COOKIES.get("csrftoken", "")
            return f"""
                <div class="btn-group pull-right">
                    <a class="btn btn-default btn-sm" href="{update_url}" title="Edytuj" data-toggle="tooltip">
                        <i class="fa fa-pencil"></i>
                    </a>
                    <form method="post" action="{delete_url}" style="display: inline;">
                        <input type="hidden" name="csrfmiddlewaretoken" value="{csrf}">
                        <button type="submit" class="btn btn-default btn-sm" title="Usuń" data-toggle="tooltip"
                                onclick="return confirm('Usunąć odczyt?');">
                            <i class="fa fa-trash"></i>
                        </button>
                    </form>
                </div>
            """

        return super().render_column(row, column)

    def customize_row(self, row, obj):
        row["row_href"] = reverse(
            "finances:meter_readings_detail", args=[obj.pk]
        )
        return row


class MeterReadingFormContextMixin:
    template_name = "meter_readings/form.html"

    def get_form_context(self, form, meter_reading=None):
        house_value = form["house"].value()
        section_value = form["section"].value()
        floor_value = form["floor"].value()
        flat_value = form["flat"].value()

        selected_house = selected_object(Houses, house_value)
        selected_section = selected_object(Sections, section_value)
        selected_floor = selected_object(Floors, floor_value)

        sections = Sections.objects.none()
        floors = Floors.objects.none()
        flats = Flats.objects.none()

        if selected_house:
            sections = Sections.objects.filter(house=selected_house).order_by(
                "title"
            )

            floors = Floors.objects.filter(house=selected_house).order_by(
                "title"
            )

        if selected_house and selected_section and selected_floor:
            flats = Flats.objects.filter(
                house=selected_house,
                section=selected_section,
                floor=selected_floor,
            ).order_by("number")

        if meter_reading:
            page_title = "Edytuj odczyt"
            form_url = reverse_lazy(
                "finances:meter_readings_update",
                kwargs={"pk": meter_reading.pk},
            )
        else:
            page_title = "Nowy odczyt"
            form_url = reverse_lazy("finances:meter_readings_create")

        return {
            "form": form,
            "sections": sections,
            "floors": floors,
            "flats": flats,
            "selected_house": selected_house,
            "selected_section": selected_section,
            "selected_floor": selected_floor,
            "selected_flat": selected_object(Flats, flat_value),
            "meter_reading": meter_reading,
            "form_url": form_url,
            "page_title": page_title,
        }


class MeterReadingsCreateView(
    RoleRequiredMixin, MeterReadingFormContextMixin, View
):
    permission_required = "has_meter_readings"

    def get(self, request):
        form = MeterReadingForm()
        return render(request, self.template_name, self.get_form_context(form))

    def post(self, request):
        form = MeterReadingForm(request.POST)
        if form.is_valid():
            meter_reading = form.save()
            messages.success(request, "Odczyt zapisano.")
            if "action_save_add" in request.POST:
                return redirect(reverse_lazy("finances:meter_readings_create"))
            return redirect(
                reverse_lazy(
                    "finances:meter_readings_detail",
                    kwargs={"pk": meter_reading.pk},
                )
            )
        else:
            print(form.errors)
            # return render(request, self.template_name, self.get_form_context(form))

        return render(request, self.template_name, self.get_form_context(form))


class MeterReadingsUpdateView(
    RoleRequiredMixin, MeterReadingFormContextMixin, View
):
    permission_required = "has_meter_readings"

    def get_object(self, pk):
        return get_object_or_404(MeterReadings, pk=pk)

    def get(self, request, pk):
        meter_reading = self.get_object(pk)
        form = MeterReadingForm(instance=meter_reading)
        return render(
            request,
            self.template_name,
            self.get_form_context(form, meter_reading),
        )

    def post(self, request, pk):
        meter_reading = self.get_object(pk)
        form = MeterReadingForm(request.POST, instance=meter_reading)
        if form.is_valid():
            meter_reading = form.save()
            messages.success(request, "Odczyt zapisano.")
            if "action_save_add" in request.POST:
                return redirect(reverse_lazy("finances:meter_readings_create"))
            return redirect(
                reverse_lazy(
                    "finances:meter_readings_detail",
                    kwargs={"pk": meter_reading.pk},
                )
            )
        else:
            print(form.errors)

        return render(
            request,
            self.template_name,
            self.get_form_context(form, meter_reading),
        )


class MeterReadingsDetailView(RoleRequiredMixin, DetailView):
    permission_required = "has_meter_readings"
    model = MeterReadings
    template_name = "meter_readings/detail.html"
    context_object_name = "meter_reading"

    def get_queryset(self):
        return MeterReadings.objects.select_related(
            "flat",
            "flat__house",
            "flat__section",
            "flat__floor",
            "flat__owner",
            "meter_type",
            "meter_type__unit_of_measurement",
        )

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["page_title"] = f"Odczyt nr{self.object.random_number}"
        context["breadcrumbs"] = [
            {
                "title": "Liczniki",
                "url": reverse_lazy("finances:meter_readings_list"),
            },
            {
                "title": self.object.random_number,
                "url": reverse_lazy(
                    "finances:meter_readings_detail",
                    kwargs={"pk": self.object.pk},
                ),
            },
        ]
        return context


class MeterReadingsDeleteView(RoleRequiredMixin, View):
    permission_required = "has_meter_readings"
    success_url = reverse_lazy("finances:meter_readings_list")

    def post(self, request, pk):
        meter_reading = get_object_or_404(MeterReadings, pk=pk)
        number = meter_reading.random_number
        meter_reading.delete()
        messages.success(request, f"Odczyt nr{number} usunięto.")
        return redirect(self.success_url)
