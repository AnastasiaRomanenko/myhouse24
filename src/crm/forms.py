from datetime import datetime

from django import forms
from django.utils import timezone

from src.buildings.models import Flats
from src.finances.models import Requests
from src.users.models import Users


class ProfileForm(forms.ModelForm):
    class Meta:
        model = Users
        fields = [
            "first_name",
            "last_name",
            "patronimic_name",
            "phone_number",
            "viber",
            "telegram",
            "email",
            "image",
            "notes",
        ]
        widgets = {
            "first_name": forms.TextInput(attrs={"class": "form-control"}),
            "last_name": forms.TextInput(attrs={"class": "form-control"}),
            "patronimic_name": forms.TextInput(
                attrs={"class": "form-control"}
            ),
            "phone_number": forms.TextInput(attrs={"class": "form-control"}),
            "viber": forms.TextInput(attrs={"class": "form-control"}),
            "telegram": forms.TextInput(attrs={"class": "form-control"}),
            "email": forms.EmailInput(attrs={"class": "form-control"}),
            "image": forms.FileInput(attrs={"class": "form-control"}),
            "notes": forms.Textarea(
                attrs={"class": "form-control", "rows": 5}
            ),
        }


MASTER_TYPE_CHOICES = (
    ("any", "Dowolny specjalista"),
    ("plumber", "Hydraulik"),
    ("electrician", "Elektryk"),
    ("locksmith", "Ślusarz"),
)


class MasterRequestForm(forms.ModelForm):
    master_type = forms.ChoiceField(
        choices=MASTER_TYPE_CHOICES,
        required=False,
    )
    date_request = forms.DateField(
        input_formats=["%d.%m.%Y", "%Y-%m-%d"],
        widget=forms.TextInput(attrs={"class": "form-control"}),
    )
    time_request = forms.TimeField(
        required=False,
        input_formats=["%H:%M"],
        widget=forms.TextInput(attrs={"class": "form-control"}),
    )

    class Meta:
        model = Requests
        fields = ["flat", "description"]
        widgets = {
            "flat": forms.Select(attrs={"class": "form-control"}),
            "description": forms.Textarea(
                attrs={"class": "form-control", "rows": 5}
            ),
        }

    def __init__(self, *args, owner=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.owner = owner
        flats = Flats.objects.select_related("house")
        if owner is not None:
            flats = flats.filter(owner=owner)
        self.fields["flat"].queryset = flats.order_by("house__title", "number")
        self.fields["flat"].empty_label = "Wybierz..."

    def save(self, commit=True):
        instance = super().save(commit=False)

        date_request = self.cleaned_data.get("date_request")
        time_request = self.cleaned_data.get("time_request")
        if date_request:
            naive = datetime.combine(
                date_request, time_request or datetime.min.time()
            )
            instance.date_time = timezone.make_aware(
                naive, timezone.get_current_timezone()
            )

        master_type = self.cleaned_data.get("master_type")
        label = dict(MASTER_TYPE_CHOICES).get(master_type)
        if label and label not in (instance.description or ""):
            instance.description = f"[{label}] {instance.description}"

        if self.owner is not None:
            instance.owner = self.owner

        if not instance.status:
            instance.status = "new"

        if commit:
            instance.save()
        return instance
