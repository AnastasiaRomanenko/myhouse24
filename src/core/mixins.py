from django.contrib import messages
from django.contrib.auth.mixins import AccessMixin, UserPassesTestMixin
from django.contrib.auth.views import redirect_to_login
from django.shortcuts import redirect
from django.urls import reverse_lazy

from src.users.enums import Status


class RoleRequiredMixin(AccessMixin):

    permission_required = None

    def get_permission_required(self):
        return str(self.permission_required)

    def dispatch(self, request, *args, **kwargs):
        user = request.user

        if not user.is_authenticated:
            return redirect("authentication:login")

        if (
            not user.is_staff
            or not user.is_active
            or user.status != Status.ACTIVE
        ):
            return redirect("authentication:login")

        if self.permission_required is None:
            return super().dispatch(request, *args, **kwargs)

        role = getattr(user, "role", None)
        if not role or not getattr(
            role, self.get_permission_required(), False
        ):
            messages.error(
                request,
                "Brak dostępu do tej strony. Skontaktuj się z administracją.",
            )
            return redirect(
                reverse_lazy("users:admin_profile", kwargs={"pk": user.id})
            )

        return super().dispatch(request, *args, **kwargs)


class SuperuserRequiredMixin(UserPassesTestMixin):
    def test_func(self):
        user = self.request.user
        return (
            user.is_authenticated
            and user.is_staff
            and user.is_superuser
            and user.is_active
            and user.status == Status.ACTIVE
        )

    def handle_no_permission(self):
        return redirect_to_login(self.request.get_full_path())


class StaffRequiredMixin(UserPassesTestMixin):
    def test_func(self):
        user = self.request.user
        return (
            user.is_authenticated
            and user.is_staff
            and user.is_active
            and user.status == Status.ACTIVE
        )

    def handle_no_permission(self):
        return redirect_to_login(self.request.get_full_path())


class OwnerRequiredMixin(UserPassesTestMixin):
    def test_func(self):
        user = self.request.user
        return (
            user.is_authenticated
            and not user.is_staff
            and user.is_active
            and user.status == Status.ACTIVE
        )

    def handle_no_permission(self):
        return redirect_to_login(self.request.get_full_path())
