from ajax_datatable import AjaxDatatableView
from django.shortcuts import redirect
from django.urls import reverse, reverse_lazy
from django.views.generic import TemplateView

from src.core.mixins import StaffRequiredMixin
from src.users.models import Roles

PERMISSION_FIELDS = [
    "has_statistics",
    "has_cash_register",
    "has_payment_receipts",
    "has_bank_books",
    "has_flats",
    "has_flats_owners",
    "has_houses",
    "has_messages",
    "has_requests",
    "has_meter_readings",
    "has_site_management",
    "has_services",
    "has_tariffs",
    "has_roles",
    "has_users",
    "has_payment_details",
    "has_payment_items",
]

PERMISSION_TITLES = [
    ("has_statistics", "Statystyki"),
    ("has_cash_register", "Kasa"),
    ("has_payment_receipts", "Rachunki do zapłaty"),
    ("has_bank_books", "Konta osobiste"),
    ("has_flats", "Mieszkania"),
    ("has_flats_owners", "Właściciele mieszkań"),
    ("has_houses", "Budynki"),
    ("has_messages", "Wiadomości"),
    ("has_requests", "Zgłoszenia serwisowe"),
    ("has_meter_readings", "Liczniki"),
    ("has_site_management", "Zarządzanie stroną"),
    ("has_services", "Usługi"),
    ("has_tariffs", "Taryfy"),
    ("has_roles", "Role"),
    ("has_users", "Użytkownicy"),
    ("has_payment_details", "Dane płatnicze"),
    ("has_payment_items", "Pozycje płatności"),
]


class RolesListView(StaffRequiredMixin, TemplateView):
    template_name = "roles/list.html"
    permission_required = "has_roles"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["page_title"] = "Role"
        context["breadcrumbs"] = [
            {
                "title": "Role",
                "url": reverse_lazy("users:roles_list"),
            },
        ]
        context["permission_columns"] = PERMISSION_TITLES
        return context

    def post(self, request, *args, **kwargs):
        roles = Roles.objects.all()

        for role in roles:
            for perm in PERMISSION_FIELDS:
                checkbox_name = f"{perm}[{role.role}]"
                setattr(role, perm, checkbox_name in request.POST)

            role.save()

        return redirect(reverse("users:roles_list"))


class RolesAjaxDatatableView(StaffRequiredMixin, AjaxDatatableView):
    model = Roles
    title = "Role"
    initial_order = [["id", "asc"]]
    length_menu = [[50], [50]]
    permission_required = "has_roles"

    column_defs = [{"name": "role", "title": "Rola"}] + [
        {"name": field, "title": title} for field, title in PERMISSION_TITLES
    ]

    def get_initial_queryset(self, request=None):
        return Roles.objects.all().order_by("id")

    def render_column(self, row, column):
        if column == "role":
            return row.role

        if column in PERMISSION_FIELDS:
            checked = " checked" if getattr(row, column) else ""
            return (
                f'<input type="checkbox" name="{column}[{row.role}]" '
                f'value="1"{checked}>'
            )

        return super().render_column(row, column)
