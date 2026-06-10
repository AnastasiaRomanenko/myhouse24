from ajax_datatable import AjaxDatatableView
from django.contrib import messages
from django.contrib.auth import get_user_model
from django.contrib.auth.tokens import default_token_generator
from django.db.models import Q
from django.http import JsonResponse
from django.shortcuts import redirect, render
from django.template.loader import render_to_string
from django.urls import reverse, reverse_lazy
from django.utils.encoding import force_bytes
from django.utils.http import urlsafe_base64_encode
from django.views import View
from django.views.generic import (
    CreateView,
    DeleteView,
    DetailView,
    TemplateView,
    UpdateView,
)

from src.buildings.views.flats import owner_label
from src.core.mixins import RoleRequiredMixin
from src.core.select2 import request_page, request_term, select2_response
from src.users.forms import OwnerForm, OwnerInviteForm
from src.users.tasks import send_bulk_emails

Users = get_user_model()


# Create your views here.
class OwnersListView(RoleRequiredMixin, TemplateView):
    permission_required = "has_flats_owners"
    template_name = "owners/list.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        context["page_title"] = "Właściciele mieszkań"
        context["breadcrumbs"] = [
            {
                "title": "Właściciele mieszkań",
                "url": reverse_lazy("users:owner_list"),
            },
        ]
        return context


class OwnersAjaxDatatableView(RoleRequiredMixin, AjaxDatatableView):
    permission_required = "has_flats_owners"
    model = Users
    title = "Właściciele"
    initial_order = [["external_id", "asc"]]
    length_menu = [[10, 25, 50], [10, 25, 50]]

    column_defs = [
        {"name": "external_id", "title": "ID"},
        {"name": "full_name", "title": "Imię i nazwisko"},
        {"name": "phone_number", "title": "Telefon"},
        {"name": "email", "title": "Email"},
        {"name": "house", "title": "Budynek"},
        {"name": "flat", "title": "Mieszkanie"},
        {"name": "date_joined", "title": "Dodano"},
        {"name": "status", "title": "Status"},
        {"name": "dept", "title": "Dług"},
        {"name": "actions", "title": ""},
    ]

    def get_initial_queryset(self, request=None):
        qs = Users.objects.filter(is_staff=False).prefetch_related(
            "flats_set__house"
        )

        if request is None:
            return qs
        external_id = request.GET.get("external_id", "").strip()
        full_name = request.GET.get("full_name", "").strip()
        phone_number = request.GET.get("phone_number", "").strip()
        email = request.GET.get("email", "").strip()
        house = request.GET.get("house", "").strip()
        flat = request.GET.get("flat", "").strip()
        date_joined = request.GET.get("date_joined", "").strip()
        status = request.GET.get("status", "").strip()
        dept = request.GET.get("dept", "").strip()

        if external_id:
            if external_id.isdigit():
                qs = qs.filter(external_id=external_id)
            else:
                qs = qs.none()

        if full_name:
            qs = qs.filter(
                Q(first_name__icontains=full_name)
                | Q(last_name__icontains=full_name)
                | Q(patronimic_name__icontains=full_name)
            )

        if phone_number:
            qs = qs.filter(phone_number__icontains=phone_number)

        if email:
            qs = qs.filter(email__icontains=email)

        if house:
            if house.isdigit():
                qs = qs.filter(flats__house_id=house).distinct()
            else:
                qs = qs.none()

        if flat:
            if flat.isdigit():
                qs = qs.filter(flats__number=flat).distinct()
            else:
                qs = qs.none()

        if date_joined:
            qs = qs.filter(date_joined__gte=date_joined)

        if status:
            qs = qs.filter(status=status)

        if dept:
            pass

        return qs

    def render_column(self, row, column):
        if column == "external_id":
            return row.external_id or "-"

        if column == "full_name":
            parts = [row.first_name, row.last_name, row.patronimic_name]
            full_name = " ".join(p for p in parts if p)
            return full_name or "<span class='not-set'>(nie ustawiono)</span>"

        if column == "phone_number":
            return row.phone_number or "-"

        if column == "email":
            return row.email or "-"

        if column == "house":
            houses = []
            for owner_flat in row.flats_set.all():
                if owner_flat.house and owner_flat.house.title not in houses:
                    houses.append(owner_flat.house.title)
            return "<br>".join(houses) or "-"

        if column == "flat":
            flats = [
                str(owner_flat.number) for owner_flat in row.flats_set.all()
            ]
            return "<br>".join(flats) or "-"

        if column == "date_joined":
            return row.date_joined or "-"

        if column == "status":
            if row.status == "active":
                return '<small class="label label-success">Aktywny</small>'
            elif row.status == "new":
                return '<small class="label label-warning">Nowy</small>'
            return '<small class="label label-danger">Nieaktywny</small>'

        if column == "dept":
            return "-"

        if column == "actions":
            # message_url = reverse("users:owner_message", args=[row.pk])
            update_url = reverse("users:owner_update", args=[row.pk])
            delete_url = reverse("users:owner_delete", args=[row.pk])

            csrf = self.request.COOKIES.get("csrftoken", "")

            return f"""
                <div class="btn-group pull-right">
                    <a class="btn btn-default btn-sm" href=#>
                        <i class="fa fa-envelope"></i>
                    </a>
                    <a class="btn btn-default btn-sm" href="{update_url}">
                        <i class="fa fa-pencil"></i>
                    </a>
                    <form method="POST" action="{delete_url}" style="display: inline;">
                        <input type="hidden" name="csrfmiddlewaretoken" value="{csrf}">
                        <button type="submit" class="btn btn-default btn-sm"
                                onclick="return confirm('Czy na pewno chcesz usunąć ten element?');">
                            <i class="fa fa-trash"></i>
                        </button>
                    </form>
                </div>
            """

        return super().render_column(row, column)

    def customize_row(self, row, obj):
        row["row_href"] = reverse("users:owner_profile", args=[obj.pk])
        return row


class OwnerCreateView(RoleRequiredMixin, CreateView):
    permission_required = "has_flats_owners"
    model = Users
    form_class = OwnerForm
    template_name = "owners/form.html"
    success_url = reverse_lazy("users:owner_list")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["page_title"] = "Nowy właściciel"
        context["breadcrumbs"] = [
            {
                "title": "Właściciele",
                "url": reverse_lazy("users:owner_list"),
            },
            {
                "title": "Nowy właściciel",
                "url": reverse_lazy("users:owner_create"),
            },
        ]
        return context

    def form_valid(self, form):
        response = super().form_valid(form)
        form.save()
        messages.success(self.request, "Użytkownik utworzono.")
        return response

    def form_invalid(self, form):
        print(form.errors)
        return super().form_invalid(form)


class OwnerProfileView(RoleRequiredMixin, DetailView):
    permission_required = "has_flats_owners"
    model = Users
    template_name = "owners/profile.html"
    context_object_name = "owner"

    def get_queryset(self):
        return Users.objects.filter(is_staff=False)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        context["page_title"] = "Właściciele mieszkań"
        context["breadcrumbs"] = [
            {
                "title": "Właściciele mieszkań",
                "url": reverse_lazy("users:owner_list"),
            },
            {
                "title": "Profil właściciela",
                "url": reverse_lazy(
                    "users:owner_profile", kwargs={"pk": self.object.pk}
                ),
            },
        ]
        return context


class OwnerUpdateView(RoleRequiredMixin, UpdateView):
    permission_required = "has_flats_owners"
    model = Users
    form_class = OwnerForm
    template_name = "owners/form.html"
    success_url = reverse_lazy("users:owner_list")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["page_title"] = "Właściciele mieszkań"
        context["breadcrumbs"] = [
            {
                "title": "Właściciele mieszkań",
                "url": reverse_lazy("users:owner_list"),
            },
            {
                "title": "Profil właściciela",
                "url": reverse_lazy(
                    "users:owner_profile", kwargs={"pk": self.object.pk}
                ),
            },
            {
                "title": "Edycja",
                "url": reverse_lazy(
                    "users:owner_update", kwargs={"pk": self.object.pk}
                ),
            },
        ]
        return context

    def form_valid(self, form):
        print("Form is valid, saving owner %s", self.object.pk)
        messages.success(self.request, "Użytkownik zaktualizowano.")
        return super().form_valid(form)

    def form_invalid(self, form):
        print("Form invalid: %s", form.errors)
        return super().form_invalid(form)


class OwnerDeleteView(RoleRequiredMixin, DeleteView):
    permission_required = "has_flats_owners"
    model = Users
    success_url = reverse_lazy("users:owner_list")

    def post(self, request):
        form = OwnerInviteForm(request.POST)

        if form.is_valid():
            email = form.cleaned_data["email"]
            try:
                user = Users.objects.get(email=email)
                uidb64 = urlsafe_base64_encode(force_bytes(user.pk))
                token = default_token_generator.make_token(user)

                body = render_to_string(
                    self.html_email_template_name,
                    {
                        "user": user,
                        "token": token,
                        "uid": uidb64,
                        "protocol": "https" if request.is_secure() else "http",
                        "domain": request.get_host(),
                    },
                )

                send_bulk_emails.delay("Zaproszenie do MyHouse24", body, email)

                messages.success(request, f"Zaproszenie wysłano na {email}.")
                return redirect(reverse_lazy("users:owner_list"))
            except Users.DoesNotExist:
                return redirect(reverse_lazy("users:owner_invite"))

        return render(
            request,
            self.template_name,
            {
                "form": form,
                "page_title": "Wyślij zaproszenie",
                "breadcrumbs": [
                    {
                        "title": "Właściciele",
                        "url": reverse_lazy("users:owner_list"),
                    },
                    {
                        "title": "Wyślij zaproszenie",
                        "url": reverse_lazy("users:owner_invite"),
                    },
                ],
            },
        )


class OwnerSelect2View(RoleRequiredMixin, View):
    def get(self, request):
        term = request_term(request)
        queryset = Users.objects.filter(is_staff=False).order_by(
            "last_name",
            "first_name",
            "email",
        )

        if term:
            owner_filter = (
                Q(first_name__icontains=term)
                | Q(last_name__icontains=term)
                | Q(patronimic_name__icontains=term)
                | Q(email__icontains=term)
            )
            if term.isdigit():
                owner_filter |= Q(external_id=int(term))
            queryset = queryset.filter(owner_filter)

        return JsonResponse(
            select2_response(
                queryset,
                request_page(request),
                owner_label,
            )
        )
