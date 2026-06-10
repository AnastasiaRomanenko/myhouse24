from django.urls import path

from src.main.views import website, website_management

app_name = "main"

urlpatterns = [
    path("", website.WebsiteMainView.as_view(), name="home_page"),
    path("about/", website.WebsiteAboutView.as_view(), name="about_page"),
    path(
        "services/",
        website.WebsiteServicesView.as_view(),
        name="services_page",
    ),
    path(
        "contacts/",
        website.WebsiteContactsView.as_view(),
        name="contacts_page",
    ),
    path(
        "website-management/main/",
        website_management.MainUpdateView.as_view(),
        name="main_update",
    ),
    path(
        "website-management/about/",
        website_management.AboutUpdateView.as_view(),
        name="about_update",
    ),
    path(
        "website-management/services/",
        website_management.ServicesUpdateView.as_view(),
        name="services_update",
    ),
    path(
        "website-management/services/<int:pk>/delete/",
        website_management.ServiceDeleteView.as_view(),
        name="service_delete",
    ),
    path(
        "website-management/contacts/",
        website_management.ContactUpdateView.as_view(),
        name="contact_update",
    ),
]
