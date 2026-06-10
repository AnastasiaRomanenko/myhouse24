from ajax_datatable.views import AjaxDatatableView
from django.contrib import messages
from django.contrib.auth import get_user_model
from django.contrib.auth.tokens import default_token_generator
from django.db.models import Q
from django.shortcuts import get_object_or_404, redirect
from django.template.loader import render_to_string
from django.urls import reverse, reverse_lazy
from django.utils.encoding import force_bytes
from django.utils.http import urlsafe_base64_encode
from django.views import View
from django.views.generic import (
    CreateView,
    DetailView,
    TemplateView,
    UpdateView,
)

from src.users.forms import UserForm
from src.users.models import Roles
from src.users.tasks import send_bulk_emails

Users = get_user_model()


class UsersListView(TemplateView):
    template_name = "users/list.html"
    permission_required = "has_users"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        context["page_title"] = "Użytkownicy"
        context["breadcrumbs"] = [
            {
                "title": "Użytkownicy",
                "url": reverse_lazy("users:admin_list"),
            },
        ]
        return context


class UsersAjaxDatatableView(AjaxDatatableView):
    model = Users
    title = "Użytkownicy"
    initial_order = [["id", "asc"]]
    length_menu = [[10, 25, 50], [10, 25, 50]]
    permission_required = "has_users"

    column_defs = [
        {"name": "pk", "title": "ID"},
        {"name": "full_name", "title": "Użytkownik"},
        {"name": "role", "title": "Rola"},
        {"name": "phone_number", "title": "Telefon"},
        {"name": "email", "title": "Email"},
        {"name": "status", "title": "Status"},
        {"name": "actions", "title": ""},
    ]

    def get_initial_queryset(self, request=None):
        qs = Users.objects.filter(is_staff=True).select_related("role")

        if request is None:
            return qs
        full_name = request.GET.get("full_name", "").strip()
        role = request.GET.get("role", "").strip()
        phone_number = request.GET.get("phone_number", "").strip()
        email = request.GET.get("email", "").strip()
        status = request.GET.get("status", "").strip()

        if full_name:
            qs = qs.filter(
                Q(first_name__icontains=full_name)
                | Q(last_name__icontains=full_name)
                | Q(patronimic_name__icontains=full_name)
            )

        if role:
            qs = qs.filter(role__role__iexact=role)

        if phone_number:
            qs = qs.filter(phone_number__icontains=phone_number)

        if email:
            qs = qs.filter(email__icontains=email)

        if status:
            qs = qs.filter(status=status)

        return qs

    def render_column(self, row, column):
        if column == "id":
            return str(row.id)

        if column == "full_name":
            return (
                row.get_full_name()
                or "<span class='not-set'>(nie ustawiono)</span>"
            )

        if column == "role":
            return row.role.role if row.role else "—"

        if column == "status":
            if row.status == "active":
                return '<small class="label label-success">Aktywny</small>'
            elif row.status == "new":
                return '<small class="label label-warning">Nowy</small>'
            return '<small class="label label-danger">Nieaktywny</small>'

        if column == "actions":
            invite_url = reverse("users:admin_invite", args=[row.pk])
            update_url = reverse("users:admin_update", args=[row.pk])
            delete_url = reverse("users:admin_delete", args=[row.pk])

            delete_button_class = "disabled" if row.is_superuser else ""
            invite_button_class = "disabled" if row.is_active else ""

            delete_onclick = (
                "return false;"
                if row.is_superuser
                else "return confirm('Czy na pewno chcesz usunąć ten element?');"
            )
            invite_onclick = (
                "return false;"
                if row.is_active
                else "return confirm('Czy na pewno chcesz wysłać zaproszenie?');"
            )

            csrf = self.request.COOKIES.get("csrftoken", "")

            return f"""
                <div class="btn-group pull-right">
                    <form method="POST" action="{invite_url}" style="display: inline;">
                        <input type="hidden" name="csrfmiddlewaretoken" value="{csrf}">
                        <button type="submit" class="btn btn-default btn-sm {invite_button_class}"
                                onclick="{invite_onclick}">
                            <i class="fa fa-envelope"></i>
                        </button>
                    </form>
                    <a class="btn btn-default btn-sm" href="{update_url}">
                        <i class="fa fa-pencil"></i>
                    </a>
                    <form method="POST" action="{delete_url}" style="display: inline;">
                        <input type="hidden" name="csrfmiddlewaretoken" value="{csrf}">
                        <button type="submit" class="btn btn-default btn-sm {delete_button_class}"
                                onclick="{delete_onclick}">
                            <i class="fa fa-trash"></i>
                        </button>
                    </form>
                </div>
            """

        return super().render_column(row, column)

    def customize_row(self, row, obj):
        row["row_href"] = reverse("users:admin_profile", args=[obj.pk])
        return row


class UserProfileView(DetailView):
    model = Users
    template_name = "users/profile.html"
    context_object_name = "admin_user"
    permission_required = "has_users"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        context["page_title"] = "Użytkownicy"
        context["breadcrumbs"] = [
            {
                "title": "Użytkownicy",
                "url": reverse_lazy("users:admin_list"),
            },
            {
                "title": "Użytkownik",
                "url": reverse_lazy(
                    "users:admin_profile", kwargs={"pk": self.object.pk}
                ),
            },
        ]
        return context


class UserCreateView(CreateView):
    model = Users
    form_class = UserForm
    template_name = "users/form.html"
    success_url = reverse_lazy("users:admin_list")
    permission_required = "has_users"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["roles"] = Roles.objects.all()

        context["page_title"] = "Użytkownicy"
        context["breadcrumbs"] = [
            {
                "title": "Użytkownicy",
                "url": reverse_lazy("users:admin_list"),
            },
            {
                "title": "Nowy użytkownik",
                "url": reverse_lazy("users:admin_create"),
            },
        ]
        return context

    def form_valid(self, form):
        response = super().form_valid(form)
        if not self.object.is_staff:
            self.object.is_staff = True
            self.object.save(update_fields=["is_staff"])
        messages.success(self.request, "Użytkownik utworzono.")
        return response

    def form_invalid(self, form):
        print(form.errors)
        return super().form_invalid(form)


class UserUpdateView(UpdateView):
    model = Users
    form_class = UserForm
    template_name = "users/form.html"
    success_url = reverse_lazy("users:admin_list")
    permission_required = "has_users"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["roles"] = Roles.objects.all()
        context["page_title"] = "Użytkownicy"
        context["breadcrumbs"] = [
            {"title": "Użytkownicy", "url": reverse_lazy("users:admin_list")},
            {
                "title": "Użytkownik",
                "url": reverse_lazy(
                    "users:admin_update", kwargs={"pk": self.object.pk}
                ),
            },
        ]
        return context

    def form_valid(self, form):
        print("Form is valid, saving user %s", self.object.pk)
        messages.success(self.request, "Użytkownik zaktualizowano.")
        return super().form_valid(form)

    def form_invalid(self, form):
        print("Form invalid: %s", form.errors)
        return super().form_invalid(form)


class UserDeleteView(View):
    model = Users
    success_url = reverse_lazy("users:admin_list")
    template_name = None
    permission_required = "has_users"

    def post(self, request, pk, *args, **kwargs):
        obj = get_object_or_404(self.model, pk=pk)
        title = obj.first_name
        obj.delete()
        messages.success(request, f"Użytkownik: {title} usunięto.")
        return redirect(self.success_url)


class UserInviteView(DetailView):
    model = Users
    html_email_template_name = "users/invitation_email.html"
    permission_required = "has_users"

    def post(self, request, *args, **kwargs):
        user = self.get_object()

        uidb64 = urlsafe_base64_encode(force_bytes(user.pk))
        token = default_token_generator.make_token(user)

        subject = "Potwierdź konto"

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

        send_bulk_emails.delay(subject, body, user.email)
        return redirect("users:admin_list")
