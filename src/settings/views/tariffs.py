from ajax_datatable import AjaxDatatableView
from django.contrib import messages
from django.db import transaction
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse, reverse_lazy
from django.utils.text import Truncator
from django.views import View
from django.views.generic import DetailView, TemplateView

from src.settings.forms import ServiceTariffFormSet, TariffForm
from src.settings.models import Services, ServiceTariffs, Tariffs


class TariffsListView(TemplateView):
    template_name = "tariffs/list.html"
    permission_required = "has_tariffs"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["page_title"] = "Taryfy"
        context["breadcrumbs"] = [
            {"title": "Taryfy", "url": reverse_lazy("settings:tariffs_list")},
        ]
        return context


class TariffsAjaxDatatableView(AjaxDatatableView):
    model = Tariffs
    title = "Taryfy"
    initial_order = [["title", "asc"]]
    length_menu = [[10, 25, 50], [10, 25, 50]]
    permission_required = "has_tariffs"

    column_defs = [
        {"name": "title", "title": "Nazwa taryfy"},
        {"name": "description", "title": "Opis taryfy"},
        {"name": "update_at", "title": "Data aktualizacji"},
        {"name": "actions", "title": ""},
    ]

    def get_initial_queryset(self, request=None):
        queryset = Tariffs.objects.all()

        if request is None:
            return queryset

        title = request.GET.get("title", "").strip()
        description = request.GET.get("description", "").strip()

        if title:
            queryset = queryset.filter(title__icontains=title)
        if description:
            queryset = queryset.filter(description__icontains=description)

        return queryset

    def render_column(self, row, column):
        if column == "description":
            return Truncator(row.description).chars(100)

        if column == "update_at":
            return (
                row.update_at.strftime("%d.%m.%Y - %H:%M")
                if row.update_at
                else "-"
            )

        if column == "actions":
            copy_url = (
                f"{reverse('settings:tariffs_create')}?tariff_id={row.pk}"
            )
            update_url = reverse("settings:tariffs_update", args=[row.pk])
            delete_url = reverse("settings:tariffs_delete", args=[row.pk])
            csrf = self.request.COOKIES.get("csrftoken", "")

            return f"""
                <div class="btn-group pull-right">
                    <a class="btn btn-default btn-sm" href="{copy_url}" title="Kopiuj" data-toggle="tooltip">
                        <i class="fa fa-clone"></i>
                    </a>
                    <a class="btn btn-default btn-sm" href="{update_url}" title="Edytuj" data-toggle="tooltip">
                        <i class="fa fa-pencil"></i>
                    </a>
                    <form method="post" action="{delete_url}" style="display: inline;">
                        <input type="hidden" name="csrfmiddlewaretoken" value="{csrf}">
                        <button type="submit" class="btn btn-default btn-sm" title="Usuń" data-toggle="tooltip"
                                onclick="return confirm('Czy na pewno chcesz usunąć ten element?');">
                            <i class="fa fa-trash"></i>
                        </button>
                    </form>
                </div>
            """

        return super().render_column(row, column)

    def customize_row(self, row, obj):
        row["row_href"] = reverse("settings:tariffs_detail", args=[obj.pk])
        return row


class TariffsDetailView(DetailView):
    template_name = "tariffs/detail.html"
    model = Tariffs
    context_object_name = "tariff"
    permission_required = "has_tariffs"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        tariff = self.get_object()
        context["page_title"] = "Taryfa"
        context["breadcrumbs"] = [
            {"title": "Taryfy", "url": reverse_lazy("settings:tariffs_list")},
            {
                "title": f"Taryfa: {tariff.title}",
                "url": reverse_lazy(
                    "settings:tariffs_detail", kwargs={"pk": tariff.pk}
                ),
            },
        ]
        context["tariff_services"] = ServiceTariffs.objects.filter(
            tariff=tariff
        ).select_related("service", "service__unit_of_measurement")
        return context


class TariffServicesAjaxDatatableView(AjaxDatatableView):
    model = ServiceTariffs
    title = "Usługi taryfy"
    initial_order = [["pk", "asc"]]
    length_menu = [[10, 25, 50], [10, 25, 50]]
    permission_required = "has_tariffs"

    column_defs = [
        {"name": "pk", "title": "#"},
        {"name": "service", "title": "Usługa"},
        {"name": "unit", "title": "Jedn. miary"},
        {"name": "price", "title": "Cena za jedn., zł"},
        {"name": "currency", "title": "Waluta"},
    ]

    def get_initial_queryset(self, request=None):
        return ServiceTariffs.objects.filter(
            tariff_id=self.kwargs["pk"],
        ).select_related(
            "service",
            "service__unit_of_measurement",
        )

    def render_column(self, row, column):
        if column == "service":
            return row.service.title if row.service else "-"

        if column == "unit":
            unit = (
                getattr(row.service, "unit_of_measurement", None)
                if row.service
                else None
            )
            return unit.title if unit else "-"

        if column == "currency":
            return "zł"

        return super().render_column(row, column)


class TariffsCreateView(View):
    template_name = "tariffs/form.html"
    success_url = reverse_lazy("settings:tariffs_list")
    permission_required = "has_tariffs"

    @staticmethod
    def _services_json():
        services = Services.objects.select_related("unit_of_measurement").all()
        return [
            {
                "id": s.pk,
                "title": s.title,
                "unit": (
                    s.unit_of_measurement.title
                    if s.unit_of_measurement
                    else ""
                ),
            }
            for s in services
        ]

    def get(self, request):
        tariff_id = request.GET.get("tariff_id")
        if tariff_id:
            source_tariff = Tariffs.objects.get(id=int(tariff_id))

            form = TariffForm(
                initial={
                    "title": source_tariff.title,
                    "description": source_tariff.description,
                }
            )

            service_tariffs = ServiceTariffs.objects.filter(
                tariff=source_tariff
            )

            formset = ServiceTariffFormSet(
                queryset=service_tariffs,
                initial=[
                    {"service": st.service, "price": st.price}
                    for st in service_tariffs
                ],
                prefix="services",
            )

        else:
            form = TariffForm()
            formset = ServiceTariffFormSet(
                queryset=ServiceTariffs.objects.none(), prefix="services"
            )

        return render(
            request,
            self.template_name,
            {
                "form": form,
                "formset": formset,
                "tariff": None,
                "services_json": self._services_json(),
                "page_title": "Nowa taryfa",
                "breadcrumbs": [
                    {
                        "title": "Taryfy",
                        "url": reverse_lazy("settings:tariffs_list"),
                    },
                    {
                        "title": "Nowa taryfa",
                        "url": reverse_lazy("settings:tariffs_create"),
                    },
                ],
            },
        )

    def post(self, request):
        form = TariffForm(request.POST)
        formset = ServiceTariffFormSet(
            request.POST,
            queryset=ServiceTariffs.objects.none(),
            prefix="services",
        )
        if form.is_valid() and formset.is_valid():
            with transaction.atomic():
                tariff = form.save()

                for subform in formset:
                    if not subform.cleaned_data:
                        continue
                    if subform.cleaned_data.get("DELETE"):
                        continue

                    service_tariff = subform.save(commit=False)
                    service_tariff.tariff = tariff
                    service_tariff.save()

            messages.success(request, "Taryfa utworzona.")
            return redirect(self.success_url)

        else:
            print(form.errors)
            print(formset.errors)

        return render(
            request,
            self.template_name,
            {
                "form": form,
                "formset": formset,
                "tariff": None,
                "services_json": self._services_json(),
                "page_title": "Nowa taryfa",
                "breadcrumbs": [
                    {
                        "title": "Taryfy",
                        "url": reverse_lazy("settings:tariffs_list"),
                    },
                    {
                        "title": "Nowa taryfa",
                        "url": reverse_lazy("settings:tariffs_create"),
                    },
                ],
            },
        )


class TariffsUpdateView(View):
    template_name = "tariffs/form.html"
    success_url = reverse_lazy("settings:tariffs_list")
    permission_required = "has_tariffs"

    @staticmethod
    def _services_json():
        services = Services.objects.select_related("unit_of_measurement").all()
        return [
            {
                "id": s.pk,
                "title": s.title,
                "unit": (
                    s.unit_of_measurement.title
                    if s.unit_of_measurement
                    else ""
                ),
            }
            for s in services
        ]

    def get_object(self, pk):
        return get_object_or_404(Tariffs, pk=pk)

    def get(self, request, pk):
        tariff = self.get_object(pk)
        form = TariffForm(instance=tariff)
        service_tariffs = ServiceTariffs.objects.filter(tariff=tariff)
        formset = ServiceTariffFormSet(
            queryset=service_tariffs, prefix="services"
        )

        return render(
            request,
            self.template_name,
            {
                "form": form,
                "formset": formset,
                "tariff": tariff,
                "page_title": "Edytuj taryfę",
                "breadcrumbs": [
                    {
                        "title": "Taryfy",
                        "url": reverse_lazy("settings:tariffs_list"),
                    },
                    {
                        "title": f"Taryfa: {tariff.title}",
                        "url": reverse_lazy(
                            "settings:tariffs_update", kwargs={"pk": tariff.pk}
                        ),
                    },
                ],
                "services_json": self._services_json(),
            },
        )

    def post(self, request, pk):
        tariff = self.get_object(pk)
        form = TariffForm(request.POST, instance=tariff)
        service_tariffs = ServiceTariffs.objects.filter(tariff=tariff)
        formset = ServiceTariffFormSet(
            request.POST, queryset=service_tariffs, prefix="services"
        )

        if form.is_valid() and formset.is_valid():
            with transaction.atomic():
                form.save()

                for subform in formset:
                    if not subform.cleaned_data:
                        continue

                    if subform.cleaned_data.get("DELETE"):
                        if subform.instance.pk:
                            subform.instance.delete()
                        continue

                    service_tariff = subform.save(commit=False)
                    service_tariff.tariff = tariff
                    service_tariff.save()

            messages.success(request, "Taryfa zapisana.")
            return redirect(self.success_url)
        else:
            print(formset.errors)
            print(form.errors)
        return render(
            request,
            self.template_name,
            {
                "form": form,
                "formset": formset,
                "tariff": tariff,
                "services_json": self._services_json(),
                "page_title": "Edytuj taryfę",
                "breadcrumbs": [
                    {
                        "title": "Taryfy",
                        "url": reverse_lazy("settings:tariffs_list"),
                    },
                    {
                        "title": f"Taryfa: {tariff.title}",
                        "url": reverse_lazy(
                            "settings:tariffs_update", kwargs={"pk": tariff.pk}
                        ),
                    },
                ],
            },
        )


class TariffsDeleteView(View):
    model = Tariffs
    success_url = reverse_lazy("settings:tariffs_list")
    template_name = None
    permission_required = "has_tariffs"

    def post(self, request, pk, *args, **kwargs):
        obj = get_object_or_404(self.model, pk=pk)
        title = obj.title
        obj.delete()
        messages.success(request, f"Taryfa: {title} usunięto.")
        return redirect(self.success_url)
