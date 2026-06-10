from django.views.generic import ListView, TemplateView

from src.main.models import (
    AboutUsPage,
    ContactPage,
    MainPage,
    ServicePage,
    SiteServices,
)


def contact_context(contact):
    if not contact:
        return {}

    return {
        "title": contact.title,
        "description": contact.description,
        "fullname": contact.ceo_name,
        "name": contact.ceo_name,
        "location": contact.location,
        "address": contact.address,
        "phone": contact.phone_number,
        "phone_number": contact.phone_number,
        "email": contact.email,
        "url_site": contact.web_page_url,
        "web_page_url": contact.web_page_url,
        "map_code": contact.map_url,
    }


class WebsiteMainView(TemplateView):
    template_name = "website/main.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        main_page = (
            MainPage.objects.select_related("seo")
            .prefetch_related("block")
            .first()
        )
        contact_page = ContactPage.objects.select_related("seo").first()

        context["main_page"] = main_page
        context["info_cards"] = main_page.block.all() if main_page else []
        context["contact"] = contact_context(contact_page)
        context["seo"] = main_page.seo if main_page else None
        return context


class WebsiteAboutView(TemplateView):
    template_name = "website/about.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        about_page = (
            AboutUsPage.objects.select_related("seo")
            .prefetch_related("gallery", "additional_gallery", "documents")
            .first()
        )
        context["about_page"] = about_page
        context["seo"] = about_page.seo if about_page else None
        return context


class WebsiteServicesView(ListView):
    template_name = "website/services.html"
    context_object_name = "services"
    paginate_by = 10

    def get_queryset(self):
        self.service_page = (
            ServicePage.objects.select_related("seo")
            .prefetch_related("service")
            .first()
        )
        if not self.service_page:
            return SiteServices.objects.none()
        return self.service_page.service.order_by("id")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["service_page"] = self.service_page
        context["seo"] = self.service_page.seo if self.service_page else None
        return context


class WebsiteContactsView(TemplateView):
    template_name = "website/contacts.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        contact_page = ContactPage.objects.select_related("seo").first()
        context["contact_page"] = contact_page
        context["contact_data"] = contact_context(contact_page)
        context["seo"] = contact_page.seo if contact_page else None
        return context
