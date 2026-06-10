from django.contrib import messages
from django.db import transaction
from django.shortcuts import redirect
from django.urls import reverse_lazy
from django.views.generic import TemplateView

from src.settings.forms import ServicesFormSet, UnitsOfMeasurementFormSet
from src.settings.models import Services, UnitsOfMeasurement


class ServicesUpdateView(TemplateView):
    template_name = "services/form.html"
    success_url = reverse_lazy("settings:services_update")
    permission_required = "has_payment_services"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        if "services_formset" not in context:
            context["services_formset"] = ServicesFormSet(
                queryset=Services.objects.order_by("id"),
                prefix="services",
            )

        if "units_formset" not in context:
            context["units_formset"] = UnitsOfMeasurementFormSet(
                queryset=UnitsOfMeasurement.objects.order_by("id"),
                prefix="units",
            )
        context["units"] = UnitsOfMeasurement.objects.order_by("id")
        context["page_title"] = "Edycja usług"
        context["breadcrumbs"] = [
            {
                "title": "Edycja usług",
                "url": reverse_lazy("settings:services_update"),
            },
        ]

        return context

    @transaction.atomic
    def post(self, request, *args, **kwargs):
        services_formset = ServicesFormSet(
            data=request.POST,
            queryset=Services.objects.order_by("id"),
            prefix="services",
        )
        units_formset = UnitsOfMeasurementFormSet(
            data=request.POST,
            queryset=UnitsOfMeasurement.objects.order_by("id"),
            prefix="units",
        )

        if not services_formset.is_valid() or not units_formset.is_valid():
            print(services_formset.errors)
            print(units_formset.errors)
            return self.render_to_response(
                self.get_context_data(
                    services_formset=services_formset,
                    units_formset=units_formset,
                )
            )

        units_to_delete = []
        for form in units_formset.forms:
            if form in units_formset.deleted_forms and form.instance.pk:
                units_to_delete.append(form.instance)

        blocked_units = [
            unit for unit in units_to_delete if unit.services.exists()
        ]
        if blocked_units:
            for unit in blocked_units:
                units_formset._non_form_errors = (
                    units_formset.non_form_errors().copy()
                )
                messages.error(
                    request,
                    f'Nie można usunąć jednostki miary "{unit.title}", jest używana w usługach.',
                )

            return self.render_to_response(
                self.get_context_data(
                    services_formset=services_formset,
                    units_formset=units_formset,
                )
            )

        units_formset.save()
        services_formset.save()

        return redirect(self.success_url)
