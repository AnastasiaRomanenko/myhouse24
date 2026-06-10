from django.contrib import messages
from django.db import transaction
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse_lazy
from django.views import View

from src.core.mixins import RoleRequiredMixin
from src.main.forms import (
    AboutUsPageForm,
    BlockFormSet,
    ContactPageForm,
    DocumentFormSet,
    ImageFormSet,
    MainPageForm,
    SEOForm,
    ServicePageForm,
)
from src.main.models import (
    AboutUsPage,
    ContactPage,
    MainPage,
    ServicePage,
    SiteServices,
)


class MainUpdateView(RoleRequiredMixin, View):
    permission_required = "has_site_management"
    template_name = "website_management/main.html"

    def get_context(
        self, main_page, form=None, seo_form=None, block_formset=None
    ):
        return {
            "form": form or MainPageForm(instance=main_page),
            "seo_block": seo_form
            or SEOForm(instance=main_page.seo, prefix="seo"),
            "block_formset": block_formset
            or BlockFormSet(
                queryset=main_page.block.order_by("id"),
                prefix="blocks",
            ),
            "page_title": "Edycja strony",
            "breadcrumbs": [
                {
                    "title": "Strona główna",
                    "url": reverse_lazy("main:main_update"),
                },
                {
                    "title": "Edycja strony",
                    "url": reverse_lazy("main:main_update"),
                },
            ],
        }

    def get(self, request):
        main_page = (
            MainPage.objects.select_related("seo")
            .prefetch_related("block")
            .first()
        )
        return render(request, self.template_name, self.get_context(main_page))

    @transaction.atomic
    def post(self, request):
        main_page = (
            MainPage.objects.select_related("seo")
            .prefetch_related("block")
            .first()
        )
        form = MainPageForm(request.POST, request.FILES, instance=main_page)
        seo_form = SEOForm(request.POST, instance=main_page.seo, prefix="seo")
        block_formset = BlockFormSet(
            request.POST,
            request.FILES,
            queryset=main_page.block.order_by("id"),
            prefix="blocks",
        )

        if (
            form.is_valid()
            and seo_form.is_valid()
            and block_formset.is_valid()
        ):
            main_page = form.save()
            seo_form.save()
            blocks = []

            for form in block_formset:
                if not form.cleaned_data:
                    continue

                if form.cleaned_data.get("DELETE"):
                    if form.instance.pk:
                        form.instance.delete()
                    continue

                if not form.has_content():
                    continue

                obj = form.save(commit=False)
                obj.save()
                blocks.append(obj)

            main_page.block.set(blocks)
            messages.success(request, "Strona główna zapisana.")
            return redirect(reverse_lazy("main:main_update"))
        else:
            messages.error(request, "Sprawdź błędy w formularzu.")
        return render(
            request,
            self.template_name,
            self.get_context(main_page, form, seo_form, block_formset),
        )


class AboutUpdateView(RoleRequiredMixin, View):
    permission_required = "has_site_management"
    template_name = "website_management/about.html"
    form_name = "about_us_page"

    def get_context(
        self,
        about_page,
        form=None,
        seo_form=None,
        main_gallery_formset=None,
        add_gallery_formset=None,
        document_formset=None,
    ):
        return {
            "form": form or AboutUsPageForm(instance=about_page),
            "seo_block": seo_form
            or SEOForm(instance=about_page.seo, prefix="seo"),
            "main_gallery_formset": main_gallery_formset
            or ImageFormSet(
                queryset=about_page.gallery.order_by("id"),
                prefix="main_gallery",
            ),
            "add_gallery_formset": add_gallery_formset
            or ImageFormSet(
                queryset=about_page.additional_gallery.order_by("id"),
                prefix="add_gallery",
            ),
            "document_formset": document_formset
            or DocumentFormSet(
                queryset=about_page.documents.order_by("id"),
                prefix="documents",
            ),
            "page_title": "Edycja strony",
            "breadcrumbs": [
                {
                    "title": "Strona główna",
                    "url": reverse_lazy("main:main_update"),
                },
                {
                    "title": "Edycja strony",
                    "url": reverse_lazy("main:about_update"),
                },
            ],
        }

    def get(self, request):
        about_page = (
            AboutUsPage.objects.select_related("seo")
            .prefetch_related("gallery", "additional_gallery", "documents")
            .first()
        )
        return render(
            request, self.template_name, self.get_context(about_page)
        )

    @transaction.atomic
    def post(self, request):
        about_page = (
            AboutUsPage.objects.select_related("seo")
            .prefetch_related("gallery", "additional_gallery", "documents")
            .first()
        )

        form = AboutUsPageForm(
            request.POST, request.FILES, instance=about_page
        )
        seo_form = SEOForm(request.POST, instance=about_page.seo, prefix="seo")
        main_gallery_formset = ImageFormSet(
            request.POST,
            request.FILES,
            queryset=about_page.gallery.order_by("id"),
            prefix="main_gallery",
        )
        add_gallery_formset = ImageFormSet(
            request.POST,
            request.FILES,
            queryset=about_page.additional_gallery.order_by("id"),
            prefix="add_gallery",
        )
        document_formset = DocumentFormSet(
            request.POST,
            request.FILES,
            queryset=about_page.documents.order_by("id"),
            prefix="documents",
        )

        if (
            form.is_valid()
            and seo_form.is_valid()
            and main_gallery_formset.is_valid()
            and add_gallery_formset.is_valid()
            and document_formset.is_valid()
        ):
            about_page = form.save()
            seo_form.save()
            main_gallery = []

            for image_form in main_gallery_formset:
                if not image_form.cleaned_data:
                    continue

                if image_form.cleaned_data.get("DELETE"):
                    if image_form.instance.pk:
                        image_form.instance.delete()
                    continue

                if not image_form.has_content():
                    continue

                obj = image_form.save(commit=False)
                obj.save()
                main_gallery.append(obj)

            about_page.gallery.set(main_gallery)
            additional_gallery = []

            for image_form in add_gallery_formset:
                if not image_form.cleaned_data:
                    continue

                if image_form.cleaned_data.get("DELETE"):
                    if image_form.instance.pk:
                        image_form.instance.delete()
                    continue

                if not image_form.has_content():
                    continue

                obj = image_form.save(commit=False)
                obj.save()
                additional_gallery.append(obj)

            about_page.additional_gallery.set(additional_gallery)

            saved_docs = []
            for doc_form in document_formset:
                if not doc_form.cleaned_data:
                    continue
                if doc_form.cleaned_data.get("DELETE"):
                    if doc_form.instance.pk:
                        doc_form.instance.delete()
                    continue
                if not doc_form.has_content():
                    continue
                obj = doc_form.save(commit=False)
                obj.save()
                saved_docs.append(obj)
            about_page.documents.set(saved_docs)

            messages.success(request, "Strona 'O nas' zapisana.")
            return redirect(reverse_lazy("main:about_update"))

        messages.error(request, "Sprawdź błędy w formularzu.")
        return render(
            request,
            self.template_name,
            self.get_context(
                about_page,
                form,
                seo_form,
                main_gallery_formset,
                add_gallery_formset,
                document_formset,
            ),
        )


class ServicesUpdateView(RoleRequiredMixin, View):
    permission_required = "has_site_management"
    template_name = "website_management/services.html"

    def get_context(self, service_page, form=None, seo_form=None):
        form = form or ServicePageForm(instance=service_page)
        return {
            "form": form,
            "service_formset": form.service_formset,
            "seo_block": seo_form
            or SEOForm(instance=service_page.seo, prefix="seo"),
            "page_title": "Edycja strony",
            "breadcrumbs": [
                {
                    "title": "Strona główna",
                    "url": reverse_lazy("main:main_update"),
                },
                {
                    "title": "Edycja strony",
                    "url": reverse_lazy("main:services_update"),
                },
            ],
        }

    def get(self, request):
        service_page = (
            ServicePage.objects.select_related("seo")
            .prefetch_related("service")
            .first()
        )
        return render(
            request, self.template_name, self.get_context(service_page)
        )

    @transaction.atomic
    def post(self, request):
        service_page = (
            ServicePage.objects.select_related("seo")
            .prefetch_related("service")
            .first()
        )
        form = ServicePageForm(
            request.POST, request.FILES, instance=service_page
        )
        seo_form = SEOForm(
            request.POST, instance=service_page.seo, prefix="seo"
        )

        if form.is_valid() and seo_form.is_valid():
            form.save()
            seo_form.save()
            messages.success(request, "Strona Usługi zapisana.")
            return redirect(reverse_lazy("main:services_update"))

        messages.error(request, "Sprawdź błędy w formularzu.")
        return render(
            request,
            self.template_name,
            self.get_context(service_page, form, seo_form),
        )


class ServiceDeleteView(RoleRequiredMixin, View):
    permission_required = "has_site_management"

    def get(self, request, pk):
        service_page = (
            ServicePage.objects.select_related("seo")
            .prefetch_related("service")
            .first()
        )
        service = get_object_or_404(SiteServices, pk=pk)
        service_page.service.remove(service)
        service.delete()
        messages.success(request, "Usługa usunięto.")
        return redirect(reverse_lazy("main:services_update"))

    def post(self, request, pk):
        return self.get(request, pk)


class ContactUpdateView(RoleRequiredMixin, View):
    permission_required = "has_site_management"
    template_name = "website_management/contacts.html"

    def get_context(self, contact_page, form=None, seo_form=None):
        return {
            "contact_data": contact_page,
            "seo_block": seo_form
            or SEOForm(instance=contact_page.seo, prefix="seo"),
            "form": form or ContactPageForm(instance=contact_page),
            "page_title": "Edycja strony",
            "breadcrumbs": [
                {
                    "title": "Strona główna",
                    "url": reverse_lazy("main:main_update"),
                },
                {
                    "title": "Edycja strony",
                    "url": reverse_lazy("main:contact_update"),
                },
            ],
        }

    def get(self, request):
        contact_page = ContactPage.objects.select_related("seo").first()
        return render(
            request, self.template_name, self.get_context(contact_page)
        )

    @transaction.atomic
    def post(self, request):
        contact_page = ContactPage.objects.select_related("seo").first()
        form = ContactPageForm(
            request.POST, request.FILES, instance=contact_page
        )
        seo_form = SEOForm(
            request.POST, instance=contact_page.seo, prefix="seo"
        )
        if form.is_valid() and seo_form.is_valid():
            form.save()
            seo_form.save()
            messages.success(request, "Strona Kontakty zapisana.")
            return redirect(reverse_lazy("main:contact_update"))

        messages.error(request, "Sprawdź błędy w formularzu.")
        return render(
            request,
            self.template_name,
            self.get_context(contact_page, form, seo_form),
        )
