from django import forms
from django.forms import BaseModelFormSet, modelformset_factory

from src.settings.models import (
    PaymentDetails,
    PaymentItems,
    Services,
    ServiceTariffs,
    Tariffs,
    UnitsOfMeasurement,
)


class UnitsOfMeasurementForm(forms.ModelForm):
    class Meta:
        model = UnitsOfMeasurement
        fields = ("title",)
        labels = {
            "title": "Jedn. miary",
        }
        widgets = {
            "title": forms.TextInput(attrs={"class": "form-control"}),
        }


class ServicesForm(forms.ModelForm):
    class Meta:
        model = Services
        fields = ("title", "unit_of_measurement", "show")
        labels = {
            "title": "Usługa",
            "unit_of_measurement": "Jedn. miary",
            "show": "Pokazuj w licznikach",
        }
        widgets = {
            "title": forms.TextInput(attrs={"class": "form-control"}),
            "unit_of_measurement": forms.Select(
                attrs={"class": "form-control"}
            ),
            "show": forms.CheckboxInput(),
        }


UnitsOfMeasurementFormSet = modelformset_factory(
    UnitsOfMeasurement,
    form=UnitsOfMeasurementForm,
    extra=0,
    can_delete=True,
)

ServicesFormSet = modelformset_factory(
    Services,
    form=ServicesForm,
    extra=0,
    can_delete=True,
)


class TariffForm(forms.ModelForm):
    class Meta:
        model = Tariffs
        fields = ["title", "description"]
        widgets = {
            "title": forms.TextInput(attrs={"class": "form-control"}),
            "description": forms.Textarea(
                attrs={"class": "form-control", "rows": 5}
            ),
        }


class ServiceTariffForm(forms.ModelForm):
    class Meta:
        model = ServiceTariffs
        fields = ["service", "price"]
        widgets = {
            "service": forms.Select(
                attrs={"class": "form-control service-select"}
            ),
            "price": forms.NumberInput(
                attrs={"class": "form-control", "step": "0.01"}
            ),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        services = Services.objects.select_related("unit_of_measurement")
        self.fields["service"].queryset = services
        self.fields["service"].empty_label = "Wybierz..."

    def clean_price(self):
        price = self.cleaned_data.get("price")
        if price is not None and price < 0:
            raise forms.ValidationError("Cena nie może być ujemna.")
        return price

    def clean(self):
        cleaned_data = super().clean()
        service = cleaned_data.get("service")
        price = cleaned_data.get("price")

        if service and price is None:
            raise forms.ValidationError("Podaj cenę usługi.")
        if price is not None and not service:
            raise forms.ValidationError("Wybierz usługę.")

        return cleaned_data


class BaseServiceTariffFormSet(BaseModelFormSet):
    def clean(self):
        if any(self.errors):
            return

        services_seen = []
        for form in self.forms:
            if form.cleaned_data.get("DELETE"):
                continue
            if not form.cleaned_data:
                continue

            service = form.cleaned_data.get("service")
            if service:
                if service in services_seen:
                    raise forms.ValidationError(
                        f"Usługa «{service}» dodana więcej niż raz."
                    )
                services_seen.append(service)


ServiceTariffFormSet = modelformset_factory(
    ServiceTariffs,
    form=ServiceTariffForm,
    formset=BaseServiceTariffFormSet,
    extra=0,
    can_delete=True,
)


class PaymentDetailsForm(forms.ModelForm):
    class Meta:
        model = PaymentDetails
        fields = ("company_name", "information")
        widgets = {
            "company_name": forms.TextInput(attrs={"class": "form-control"}),
            "information": forms.Textarea(
                attrs={"class": "form-control", "rows": 5}
            ),
        }


class PaymentItemsForm(forms.ModelForm):
    class Meta:
        model = PaymentItems
        fields = ["name", "type"]
        widgets = {
            "name": forms.TextInput(attrs={"class": "form-control"}),
            "type": forms.Select(attrs={"class": "form-control"}),
        }
