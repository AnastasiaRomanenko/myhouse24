from datetime import datetime

from django import forms
from django.utils import timezone

from src.buildings.models import Flats, Floors, Houses, Sections
from src.finances.enums import AccountingType, PaymentReceiptStatus
from src.finances.models import (
    Accounting,
    BankBooks,
    Messages,
    MeterReadings,
    PaymentReceipts,
    PaymentReceiptServices,
    Requests,
)
from src.finances.utils import generate_number
from src.settings.models import PaymentItems, Services, Tariffs
from src.users.models import Users


class MessagesForm(forms.ModelForm):
    class Meta:
        model = Messages
        fields = ["title", "description", "flat", "to_debtors"]
        widgets = {
            "title": forms.TextInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "Temat wiadomości",
                },
            ),
            "description": forms.Textarea(
                attrs={
                    "rows": 6,
                    "class": "compose-textarea form-control",
                    "placeholder": "Treść wiadomości",
                },
            ),
            "flat": forms.Select(attrs={"class": "form-control"}),
            "to_debtors": forms.CheckboxInput(),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["flat"].queryset = Flats.objects.select_related(
            "house",
            "owner",
        ).order_by("house__title", "number")
        self.fields["flat"].empty_label = "Wybierz..."


class MeterReadingForm(forms.ModelForm):
    created_at = forms.DateField(
        input_formats=["%d.%m.%Y", "%Y-%m-%d"],
        widget=forms.TextInput(
            attrs={"class": "form-control", "placeholder": "dd.mm.rrrr"}
        ),
    )

    house = forms.ModelChoiceField(
        queryset=Houses.objects.all(), required=True
    )

    section = forms.ModelChoiceField(
        queryset=Sections.objects.none(), required=True
    )

    floor = forms.ModelChoiceField(
        queryset=Floors.objects.none(), required=True
    )

    class Meta:
        model = MeterReadings
        fields = [
            "random_number",
            "created_at",
            "house",
            "section",
            "floor",
            "flat",
            "meter_type",
            "status",
            "current_data",
        ]
        widgets = {
            "random_number": forms.TextInput(attrs={"class": "form-control"}),
            "flat": forms.Select(attrs={"class": "form-control"}),
            "meter_type": forms.Select(attrs={"class": "form-control"}),
            "status": forms.Select(attrs={"class": "form-control"}),
            "current_data": forms.NumberInput(
                attrs={"class": "form-control", "step": "0.01"}
            ),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        house_id = self.data.get("house") or self.initial.get("house")
        section_id = self.data.get("section") or self.initial.get("section")
        floor_id = self.data.get("floor") or self.initial.get("floor")

        if house_id:
            self.fields["section"].queryset = Sections.objects.filter(
                house_id=house_id
            ).order_by("title")

            self.fields["floor"].queryset = Floors.objects.filter(
                house_id=house_id
            ).order_by("title")

        if house_id and section_id and floor_id:
            self.fields["flat"].queryset = Flats.objects.filter(
                house_id=house_id, section_id=section_id, floor_id=floor_id
            ).order_by("number")
        else:
            self.fields["flat"].queryset = Flats.objects.none()

        self.fields["flat"].empty_label = "Wybierz..."
        self.fields["meter_type"].queryset = Services.objects.select_related(
            "unit_of_measurement",
        ).order_by("title")
        self.fields["meter_type"].empty_label = "Wybierz..."

        if self.instance and self.instance.pk and self.instance.created_at:
            self.fields["created_at"].initial = (
                self.instance.created_at.strftime("%d.%m.%Y")
            )


class RequestForm(forms.ModelForm):
    date_request = forms.DateField(
        required=False,
        input_formats=["%d.%m.%Y", "%Y-%m-%d"],
        widget=forms.TextInput(
            attrs={"class": "form-control", "placeholder": "dd.mm.rrrr"}
        ),
    )
    time_request = forms.TimeField(
        required=False,
        input_formats=["%H:%M"],
        widget=forms.TextInput(
            attrs={"class": "form-control", "placeholder": "gg:mm"}
        ),
    )

    class Meta:
        model = Requests
        fields = [
            "description",
            "flat",
            "owner",
            "worker",
            "status",
            "comment",
        ]
        widgets = {
            "description": forms.Textarea(
                attrs={"class": "form-control", "rows": 8}
            ),
            "flat": forms.Select(attrs={"class": "form-control"}),
            "owner": forms.Select(attrs={"class": "form-control"}),
            "worker": forms.Select(attrs={"class": "form-control"}),
            "status": forms.Select(attrs={"class": "form-control"}),
            "comment": forms.Textarea(
                attrs={"class": "compose-textarea form-control", "rows": 8}
            ),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["flat"].queryset = Flats.objects.select_related(
            "house",
            "owner",
        ).order_by("house__title", "number")
        self.fields["flat"].empty_label = "Wybierz..."
        self.fields["owner"].queryset = Users.objects.filter(
            is_staff=False
        ).order_by(
            "last_name",
            "first_name",
            "email",
        )
        self.fields["owner"].empty_label = "Wybierz..."
        self.fields["worker"].queryset = (
            Users.objects.filter(is_staff=True)
            .select_related(
                "role",
            )
            .order_by("role__role", "last_name", "first_name", "email")
        )
        self.fields["worker"].empty_label = "Wybierz..."

        if self.instance and self.instance.pk and self.instance.date_time:
            local_dt = timezone.localtime(self.instance.date_time)
            self.fields["date_request"].initial = local_dt.strftime("%d.%m.%Y")
            self.fields["time_request"].initial = local_dt.strftime("%H:%M")

    def clean(self):
        cleaned_data = super().clean()
        date_request = cleaned_data.get("date_request")
        time_request = cleaned_data.get("time_request")
        flat = cleaned_data.get("flat")

        if bool(date_request) != bool(time_request):
            raise forms.ValidationError(
                "Podaj datę i godzinę zgłoszenia razem."
            )

        if flat and not cleaned_data.get("owner"):
            cleaned_data["owner"] = flat.owner

        return cleaned_data

    def save(self, commit=True):
        instance = super().save(commit=False)
        date_request = self.cleaned_data.get("date_request")
        time_request = self.cleaned_data.get("time_request")

        if date_request and time_request:
            dt = datetime.combine(date_request, time_request)
            if timezone.is_naive(dt):
                dt = timezone.make_aware(dt, timezone.get_current_timezone())
            instance.date_time = dt
        else:
            instance.date_time = None

        if instance.flat and not instance.owner_id:
            instance.owner = instance.flat.owner

        if commit:
            instance.save()

        return instance


STATUS_CHOICES = (
    ("True", "Aktywny"),
    ("False", "Nieaktywny"),
)


class BankBookForm(forms.ModelForm):
    status = forms.TypedChoiceField(
        choices=STATUS_CHOICES,
        coerce=lambda value: value == "True",
        empty_value=False,
        required=False,
        widget=forms.Select(attrs={"class": "form-control"}),
    )

    house = forms.ModelChoiceField(
        queryset=Houses.objects.all(),
        required=False,
    )
    section = forms.ModelChoiceField(
        queryset=Sections.objects.none(),
        required=False,
    )
    floor = forms.ModelChoiceField(
        queryset=Floors.objects.none(),
        required=False,
    )

    class Meta:
        model = BankBooks
        fields = [
            "random_number",
            "status",
            "house",
            "section",
            "floor",
            "flat",
        ]
        widgets = {
            "random_number": forms.TextInput(attrs={"class": "form-control"}),
            "flat": forms.Select(attrs={"class": "form-control"}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        flat_qs = Flats.objects.select_related(
            "house", "section", "floor", "owner"
        )
        taken = BankBooks.objects.exclude(
            pk=self.instance.pk if self.instance and self.instance.pk else None
        ).values_list("flat_id", flat=True)
        self.fields["flat"].queryset = flat_qs.exclude(pk__in=taken).order_by(
            "house__title", "number"
        )
        self.fields["flat"].empty_label = "Wybierz..."

        house_id = self.data.get("house") or self.initial.get("house")
        if (
            not house_id
            and self.instance
            and self.instance.pk
            and self.instance.flat_id
        ):
            house_id = self.instance.flat.house_id

        if house_id:
            self.fields["section"].queryset = Sections.objects.filter(
                house_id=house_id
            ).order_by("title")
            self.fields["floor"].queryset = Floors.objects.filter(
                house_id=house_id
            ).order_by("title")

        if not self.instance.pk and not self.initial.get("random_number"):
            self.fields["random_number"].initial = generate_number()


class AccountingIncomeForm(forms.ModelForm):
    created_at = forms.DateField(
        input_formats=["%d.%m.%Y", "%Y-%m-%d"],
        widget=forms.TextInput(
            attrs={
                "class": "form-control krajee-datepicker",
                "placeholder": "dd.mm.rrrr",
            }
        ),
    )

    class Meta:
        model = Accounting
        fields = [
            "random_number",
            "created_at",
            "completed",
            "owner",
            "bank_book",
            "payment_item",
            "manager",
            "amount",
            "comment",
        ]
        widgets = {
            "random_number": forms.TextInput(attrs={"class": "form-control"}),
            "completed": forms.CheckboxInput(),
            "owner": forms.Select(attrs={"class": "form-control"}),
            "bank_book": forms.Select(attrs={"class": "form-control"}),
            "payment_item": forms.Select(attrs={"class": "form-control"}),
            "manager": forms.Select(attrs={"class": "form-control"}),
            "amount": forms.NumberInput(
                attrs={"class": "form-control", "step": "0.01"}
            ),
            "comment": forms.Textarea(
                attrs={"class": "form-control", "rows": 5}
            ),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["owner"].queryset = Users.objects.filter(
            is_staff=False
        ).order_by("last_name", "first_name", "email")
        self.fields["owner"].empty_label = "Wybierz..."
        self.fields["bank_book"].queryset = BankBooks.objects.select_related(
            "flat", "flat__house"
        ).order_by("random_number")
        self.fields["bank_book"].empty_label = "Wybierz..."
        self.fields["payment_item"].queryset = PaymentItems.objects.filter(
            type=AccountingType.INCOME
        ).order_by("name")
        self.fields["payment_item"].empty_label = "Wybierz..."
        self.fields["manager"].queryset = (
            Users.objects.filter(is_staff=True)
            .select_related("role")
            .order_by("last_name", "first_name", "email")
        )
        self.fields["manager"].empty_label = "Wybierz..."

        if self.instance and self.instance.pk and self.instance.created_at:
            self.fields["created_at"].initial = (
                self.instance.created_at.strftime("%d.%m.%Y")
            )
        if not self.instance.pk and not self.initial.get("random_number"):
            self.fields["random_number"].initial = generate_number()

    def save(self, commit=True):
        instance = super().save(commit=False)
        instance.type = AccountingType.INCOME
        if commit:
            instance.save()
        return instance


class AccountingExpenseForm(forms.ModelForm):
    created_at = forms.DateField(
        input_formats=["%d.%m.%Y", "%Y-%m-%d"],
        widget=forms.TextInput(
            attrs={
                "class": "form-control krajee-datepicker",
                "placeholder": "dd.mm.rrrr",
            }
        ),
    )

    class Meta:
        model = Accounting
        fields = [
            "random_number",
            "created_at",
            "completed",
            "payment_item",
            "manager",
            "amount",
            "comment",
        ]
        widgets = {
            "random_number": forms.TextInput(attrs={"class": "form-control"}),
            "completed": forms.CheckboxInput(),
            "payment_item": forms.Select(attrs={"class": "form-control"}),
            "manager": forms.Select(attrs={"class": "form-control"}),
            "amount": forms.NumberInput(
                attrs={"class": "form-control", "step": "0.01"}
            ),
            "comment": forms.Textarea(
                attrs={"class": "form-control", "rows": 5}
            ),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["payment_item"].queryset = PaymentItems.objects.filter(
            type=AccountingType.EXPENSE
        ).order_by("name")
        self.fields["payment_item"].empty_label = "Wybierz..."
        self.fields["manager"].queryset = (
            Users.objects.filter(is_staff=True)
            .select_related("role")
            .order_by("last_name", "first_name", "email")
        )
        self.fields["manager"].empty_label = "Wybierz..."

        if self.instance and self.instance.pk and self.instance.created_at:
            self.fields["created_at"].initial = (
                self.instance.created_at.strftime("%d.%m.%Y")
            )
        if not self.instance.pk and not self.initial.get("random_number"):
            self.fields["random_number"].initial = generate_number()

    def save(self, commit=True):
        instance = super().save(commit=False)
        instance.type = AccountingType.EXPENSE
        if commit:
            instance.save()
        return instance


class PaymentReceiptForm(forms.ModelForm):
    date_from = forms.DateField(
        input_formats=["%d.%m.%Y", "%Y-%m-%d"],
        widget=forms.TextInput(
            attrs={
                "class": "form-control krajee-datepicker",
                "placeholder": "dd.mm.rrrr",
            }
        ),
    )
    period_from = forms.DateField(
        input_formats=["%d.%m.%Y", "%Y-%m-%d"],
        widget=forms.TextInput(
            attrs={
                "class": "form-control krajee-datepicker",
                "placeholder": "dd.mm.rrrr",
            }
        ),
    )
    period_to = forms.DateField(
        input_formats=["%d.%m.%Y", "%Y-%m-%d"],
        widget=forms.TextInput(
            attrs={
                "class": "form-control krajee-datepicker",
                "placeholder": "dd.mm.rrrr",
            }
        ),
    )

    house = forms.ModelChoiceField(
        queryset=Houses.objects.all(),
        required=False,
        widget=forms.Select(attrs={"class": "form-control"}),
    )
    section = forms.ModelChoiceField(
        queryset=Sections.objects.none(),
        required=False,
        widget=forms.Select(attrs={"class": "form-control"}),
    )
    floor = forms.ModelChoiceField(
        queryset=Floors.objects.none(),
        required=False,
        widget=forms.Select(attrs={"class": "form-control"}),
    )

    class Meta:
        model = PaymentReceipts
        fields = [
            "random_number",
            "date_from",
            "house",
            "section",
            "floor",
            "flat",
            "completed",
            "status",
            "tariff",
            "period_from",
            "period_to",
            "bank_book",
        ]
        widgets = {
            "random_number": forms.TextInput(attrs={"class": "form-control"}),
            "flat": forms.Select(attrs={"class": "form-control"}),
            "completed": forms.CheckboxInput(),
            "status": forms.Select(attrs={"class": "form-control"}),
            "tariff": forms.Select(attrs={"class": "form-control"}),
            "bank_book": forms.Select(attrs={"class": "form-control"}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        house_id = self.data.get("house") or self.initial.get("house")
        section_id = self.data.get("section") or self.initial.get("section")
        floor_id = self.data.get("floor") or self.initial.get("floor")

        if (
            not house_id
            and self.instance
            and self.instance.pk
            and self.instance.flat_id
        ):
            house_id = self.instance.flat.house_id

        if house_id:
            self.fields["section"].queryset = Sections.objects.filter(
                house_id=house_id
            ).order_by("title")
            self.fields["floor"].queryset = Floors.objects.filter(
                house_id=house_id
            ).order_by("title")

        flat_qs = Flats.objects.select_related("house", "owner")
        if house_id and section_id and floor_id:
            flat_qs = flat_qs.filter(
                house_id=house_id, section_id=section_id, floor_id=floor_id
            )
        self.fields["flat"].queryset = flat_qs.order_by(
            "house__title", "number"
        )
        self.fields["flat"].empty_label = "Wybierz..."

        self.fields["tariff"].queryset = Tariffs.objects.order_by("title")
        self.fields["tariff"].empty_label = "Wybierz..."
        self.fields["bank_book"].queryset = BankBooks.objects.select_related(
            "flat"
        ).order_by("random_number")
        self.fields["bank_book"].empty_label = "Wybierz..."

        if not self.instance.pk:
            self.fields["status"].initial = PaymentReceiptStatus.NOT_PAID
            if not self.initial.get("random_number"):
                self.fields["random_number"].initial = generate_number()

        for field in ("date_from", "period_from", "period_to"):
            value = getattr(self.instance, field, None)
            if self.instance and self.instance.pk and value:
                self.fields[field].initial = value.strftime("%d.%m.%Y")

    def clean(self):
        cleaned_data = super().clean()
        period_from = cleaned_data.get("period_from")
        period_to = cleaned_data.get("period_to")
        if period_from and period_to and period_from > period_to:
            self.add_error(
                "period_to", "Koniec okresu jest wcześniej niż jego początek."
            )
        return cleaned_data


class PaymentReceiptServiceForm(forms.ModelForm):
    class Meta:
        model = PaymentReceiptServices
        fields = ["service", "amount", "price"]
        widgets = {
            "service": forms.Select(
                attrs={"class": "form-control service-select"}
            ),
            "price": forms.NumberInput(
                attrs={"class": "form-control svc-price", "step": "0.01"}
            ),
            "amount": forms.NumberInput(
                attrs={"class": "form-control svc-amount", "step": "0.01"}
            ),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["service"].queryset = Services.objects.select_related(
            "unit_of_measurement"
        ).order_by("title")
        self.fields["service"].empty_label = "Wybierz..."


PaymentReceiptServiceFormSet = forms.inlineformset_factory(
    PaymentReceipts,
    PaymentReceiptServices,
    form=PaymentReceiptServiceForm,
    extra=0,
    can_delete=True,
)
