from django.urls import path

from src.crm import views

app_name = "crm"

urlpatterns = [
    path("", views.ProfileView.as_view(), name="cabinet"),
    path("profile/", views.ProfileView.as_view(), name="profile"),
    path(
        "profile/edit/",
        views.ProfileUpdateView.as_view(),
        name="profile_update",
    ),
    path(
        "apartments/<int:pk>/",
        views.ApartmentSummaryView.as_view(),
        name="apartment_detail",
    ),
    path(
        "apartments/<int:pk>/tariff/",
        views.ApartmentTariffView.as_view(),
        name="apartment_tariff",
    ),
    path(
        "apartments/<int:pk>/invoices/",
        views.InvoiceListView.as_view(),
        name="apartment_invoices",
    ),
    path("invoices/", views.InvoiceListView.as_view(), name="invoice_list"),
    path(
        "invoices/ajax/",
        views.InvoiceAjaxDatatableView.as_view(),
        name="invoice_ajax",
    ),
    path(
        "invoices/<int:pk>/",
        views.InvoiceDetailView.as_view(),
        name="invoice_detail",
    ),
    path(
        "invoices/<int:pk>/download/",
        views.InvoiceDownloadView.as_view(),
        name="invoice_download",
    ),
    path(
        "invoices/<int:pk>/pay/step1/",
        views.InvoicePayStep1View.as_view(),
        name="invoice_pay_step1",
    ),
    path(
        "invoices/<int:pk>/pay/step2/",
        views.InvoicePayStep2View.as_view(),
        name="invoice_pay_step2",
    ),
    path(
        "invoices/<int:pk>/pay/card/",
        views.InvoicePayCardView.as_view(),
        name="invoice_pay_card",
    ),
    path(
        "invoices/<int:pk>/pay/success/",
        views.InvoicePaySuccessView.as_view(),
        name="invoice_pay_success",
    ),
    path("messages/", views.MessageListView.as_view(), name="message_list"),
    path(
        "messages/ajax/",
        views.MessageAjaxDatatableView.as_view(),
        name="message_ajax",
    ),
    path(
        "messages/delete/",
        views.MessageDeleteAjaxView.as_view(),
        name="message_delete_ajax",
    ),
    path(
        "messages/<int:pk>/",
        views.MessageDetailView.as_view(),
        name="message_detail",
    ),
    path("requests/", views.RequestListView.as_view(), name="request_list"),
    path(
        "requests/ajax/",
        views.RequestAjaxDatatableView.as_view(),
        name="request_ajax",
    ),
    path(
        "requests/create/",
        views.RequestCreateView.as_view(),
        name="request_create",
    ),
    path(
        "requests/<int:pk>/delete/",
        views.RequestDeleteView.as_view(),
        name="request_delete",
    ),
]
