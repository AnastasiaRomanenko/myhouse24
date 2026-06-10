from django import forms
from django.forms import inlineformset_factory

from src.buildings.models import Flats, Floors, Houses, Sections
from src.settings.models import Tariffs
from src.users.enums import Status
from src.users.models import Users


class HouseForm(forms.ModelForm):
    workers = forms.ModelMultipleChoiceField(
        queryset=Users.objects.none(),
        required=False,
        widget=forms.SelectMultiple(
            attrs={
                "class": "form-control worker-user-select",
            }
        ),
    )

    class Meta:
        model = Houses
        fields = [
            "title",
            "address",
            "image1",
            "image2",
            "image3",
            "image4",
            "image5",
            "workers",
        ]
        widgets = {
            "title": forms.TextInput(attrs={"class": "form-control"}),
            "address": forms.TextInput(attrs={"class": "form-control"}),
            "image1": forms.FileInput(attrs={"class": "form-control"}),
            "image2": forms.FileInput(attrs={"class": "form-control"}),
            "image3": forms.FileInput(attrs={"class": "form-control"}),
            "image4": forms.FileInput(attrs={"class": "form-control"}),
            "image5": forms.FileInput(attrs={"class": "form-control"}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.fields["workers"].queryset = Users.objects.select_related(
            "role"
        ).filter(
            is_active=True,
            is_staff=True,
            status=Status.ACTIVE,
        )


class FlatForm(forms.ModelForm):
    class Meta:
        model = Flats
        fields = [
            "number",
            "area",
            "house",
            "section",
            "floor",
            "owner",
            "tariff",
        ]
        widgets = {
            "number": forms.NumberInput(attrs={"class": "form-control"}),
            "area": forms.NumberInput(
                attrs={"class": "form-control", "step": "0.01"}
            ),
            "house": forms.Select(attrs={"class": "form-control"}),
            "section": forms.Select(attrs={"class": "form-control"}),
            "floor": forms.Select(attrs={"class": "form-control"}),
            "owner": forms.Select(attrs={"class": "form-control"}),
            "tariff": forms.Select(attrs={"class": "form-control"}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.fields["house"].queryset = Houses.objects.order_by("title")
        self.fields["owner"].queryset = Users.objects.filter(
            is_staff=False,
        ).order_by("last_name", "first_name", "email")
        self.fields["tariff"].queryset = Tariffs.objects.order_by("title")

        house_id = self.data.get("house") if self.is_bound else None
        if not house_id and self.instance and self.instance.pk:
            house_id = self.instance.house_id
        try:
            house_id = int(house_id) if house_id else None
        except (TypeError, ValueError):
            house_id = None

        self.fields["section"].queryset = Sections.objects.none()
        self.fields["floor"].queryset = Floors.objects.none()

        if house_id:
            self.fields["section"].queryset = Sections.objects.filter(
                house_id=house_id,
            ).order_by("title")
            self.fields["floor"].queryset = Floors.objects.filter(
                house_id=house_id,
            ).order_by("title")

    def clean(self):
        cleaned_data = super().clean()
        house = cleaned_data.get("house")
        section = cleaned_data.get("section")
        floor = cleaned_data.get("floor")

        if house and section and section.house_id != house.id:
            self.add_error(
                "section", "Sekcja nie należy do wybranego budynku."
            )

        if house and floor and floor.house_id != house.id:
            self.add_error("floor", "Piętro nie należy do wybranego budynku.")

        return cleaned_data


class SectionForm(forms.ModelForm):
    class Meta:
        model = Sections
        fields = ["title"]
        widgets = {
            "title": forms.TextInput(attrs={"class": "form-control"}),
        }


class FloorForm(forms.ModelForm):
    class Meta:
        model = Floors
        fields = ["title"]
        widgets = {
            "title": forms.TextInput(attrs={"class": "form-control"}),
        }


class HouseWorkerForm(forms.ModelForm):
    role = forms.CharField(required=False, disabled=True)

    def __init__(self, *args, **kwargs):

        super(HouseWorkerForm, self).__init__(*args, **kwargs)
        self.fields["workers"].queryset = Users.objects.select_related(
            "roles"
        ).filter(
            is_active=True,
            is_staff=True,
            status=Status.ACTIVE,
        )
        self.fields["workers"].widget.attrs.update(
            {"class": "form-control worker-user-select"}
        )

    class Meta:
        model = Houses
        fields = ["workers"]


SectionFormSet = inlineformset_factory(
    Houses, Sections, form=SectionForm, extra=0, can_delete=True
)

FloorFormSet = inlineformset_factory(
    Houses, Floors, form=FloorForm, extra=0, can_delete=True
)
