from django import forms
from django.forms import modelformset_factory

from src.main.models import (
    SEO,
    AboutUsPage,
    Blocks,
    ContactPage,
    Documents,
    Images,
    MainPage,
    ServicePage,
    SiteServices,
)


class SEOForm(forms.ModelForm):
    class Meta:
        model = SEO
        fields = ["title", "description", "keywords"]
        widgets = {
            "title": forms.TextInput(attrs={"class": "form-control"}),
            "description": forms.Textarea(
                attrs={"rows": 5, "class": "form-control"}
            ),
            "keywords": forms.Textarea(
                attrs={"rows": 3, "class": "form-control"}
            ),
        }


class MainPageForm(forms.ModelForm):
    class Meta:
        model = MainPage
        fields = [
            "title",
            "description",
            "slide1",
            "slide2",
            "slide3",
            "show_app_links",
        ]
        widgets = {
            "title": forms.TextInput(attrs={"class": "form-control"}),
            "description": forms.Textarea(
                attrs={"rows": 5, "class": "compose-textarea form-control"}
            ),
            "slide1": forms.FileInput(attrs={"class": "form-control"}),
            "slide2": forms.FileInput(attrs={"class": "form-control"}),
            "slide3": forms.FileInput(attrs={"class": "form-control"}),
            "show_app_links": forms.CheckboxInput(),
        }


class ContactPageForm(forms.ModelForm):
    class Meta:
        model = ContactPage
        fields = [
            "title",
            "description",
            "ceo_name",
            "location",
            "address",
            "phone_number",
            "email",
            "web_page_url",
            "map_url",
        ]
        widgets = {
            "title": forms.TextInput(attrs={"class": "form-control"}),
            "description": forms.Textarea(
                attrs={"rows": 5, "class": "compose-textarea form-control"}
            ),
            "ceo_name": forms.TextInput(attrs={"class": "form-control"}),
            "location": forms.TextInput(attrs={"class": "form-control"}),
            "address": forms.TextInput(attrs={"class": "form-control"}),
            "phone_number": forms.TextInput(attrs={"class": "form-control"}),
            "email": forms.EmailInput(attrs={"class": "form-control"}),
            "web_page_url": forms.URLInput(attrs={"class": "form-control"}),
            "map_url": forms.Textarea(
                attrs={"rows": 5, "class": "form-control"}
            ),
        }


class AboutUsPageForm(forms.ModelForm):

    class Meta:
        model = AboutUsPage
        fields = [
            "director_photo",
            "title",
            "description",
            "additional_title",
            "additional_description",
        ]
        widgets = {
            "director_photo": forms.FileInput(attrs={"class": "form-control"}),
            "title": forms.TextInput(attrs={"class": "form-control"}),
            "description": forms.Textarea(
                attrs={"rows": 5, "class": "compose-textarea form-control"}
            ),
            "additional_title": forms.TextInput(
                attrs={"class": "form-control"}
            ),
            "additional_description": forms.Textarea(
                attrs={"class": "compose-textarea form-control"}
            ),
        }

    def save(self, commit=True):
        instance = super().save(commit=False)
        instance.additional_title = self.cleaned_data.get(
            "additional_title", ""
        )
        instance.additional_description = self.cleaned_data.get(
            "additional_description", ""
        )
        if commit:
            instance.save()
            self.save_m2m()
        return instance


class BlockForm(forms.ModelForm):
    class Meta:
        model = Blocks
        fields = ["title", "description", "image"]
        widgets = {
            "title": forms.TextInput(attrs={"class": "form-control"}),
            "description": forms.Textarea(
                attrs={"rows": 4, "class": "compose-textarea form-control"}
            ),
            "image": forms.FileInput(attrs={"class": "form-control"}),
        }

    def has_content(self):
        return bool(
            self.cleaned_data.get("title")
            or self.cleaned_data.get("description")
            or self.cleaned_data.get("image")
            or self.instance.pk
        )


class ImageForm(forms.ModelForm):
    class Meta:
        model = Images
        fields = ["image"]
        widgets = {
            "image": forms.FileInput(attrs={"class": "form-control"}),
        }

    def has_content(self):
        return bool(self.cleaned_data.get("image") or self.instance.pk)


class SiteServiceForm(forms.ModelForm):
    class Meta:
        model = SiteServices
        fields = ["image", "title", "description"]
        widgets = {
            "image": forms.FileInput(
                attrs={"class": "form-control", "accept": "image/*"}
            ),
            "title": forms.TextInput(attrs={"class": "form-control"}),
            "description": forms.Textarea(
                attrs={
                    "rows": 5,
                    "class": "compose-textarea editor-init form-control",
                    "placeholder": "Opis tekstowy",
                },
            ),
        }

    def has_content(self):
        return bool(
            self.cleaned_data.get("title")
            or self.cleaned_data.get("description")
            or self.cleaned_data.get("image")
            or self.instance.pk
        )


class DocumentForm(forms.ModelForm):
    class Meta:
        model = Documents
        fields = ["title", "document"]
        widgets = {
            "title": forms.TextInput(attrs={"class": "form-control"}),
            "document": forms.FileInput(attrs={"class": "form-control"}),
        }

    def has_content(self):
        return bool(
            self.cleaned_data.get("title")
            or self.cleaned_data.get("document")
            or self.instance.pk
        )


DocumentFormSet = modelformset_factory(
    Documents,
    form=DocumentForm,
    extra=0,
    can_delete=True,
)

BlockFormSet = modelformset_factory(
    Blocks,
    form=BlockForm,
    extra=0,
    can_delete=True,
)

ImageFormSet = modelformset_factory(
    Images,
    form=ImageForm,
    extra=0,
    can_delete=True,
)

SiteServiceFormSet = modelformset_factory(
    SiteServices,
    form=SiteServiceForm,
    extra=0,
    can_delete=True,
)


class ServicePageForm(forms.ModelForm):
    class Meta:
        model = ServicePage
        fields = []

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        queryset = SiteServices.objects.none()
        if self.instance and self.instance.pk:
            queryset = self.instance.service.order_by("id")
        self.service_formset = SiteServiceFormSet(
            self.data if self.is_bound else None,
            self.files if self.is_bound else None,
            queryset=queryset,
            prefix="services",
        )

    def is_valid(self):
        form_is_valid = super().is_valid()
        formset_is_valid = self.service_formset.is_valid()
        return form_is_valid and formset_is_valid

    def save(self, commit=True):
        service_page = super().save(commit=commit)
        services = []

        for service_form in self.service_formset:
            if not service_form.cleaned_data:
                continue

            if service_form.cleaned_data.get("DELETE"):
                if service_form.instance.pk:
                    service_form.instance.delete()
                continue

            if not service_form.has_content():
                continue

            service = service_form.save(commit=False)
            service.save()
            services.append(service)

        if commit:
            service_page.service.set(services)

        return service_page
