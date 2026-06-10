from django.contrib.auth import views as auth_views
from django.urls import path, reverse_lazy
from django.views.generic import TemplateView

from src.authentication.views.login import CustomLoginView
from src.authentication.views.password_reset import (
    PasswordResetChangeView,
    PasswordResetRequestView,
    PasswordResetTOTPView,
)
from src.authentication.views.registration import (
    CustomRegistrationView,
    RegistrationCompleteView,
)

app_name = "authentication"

urlpatterns = [
    path("login/", CustomLoginView.as_view(), name="login"),
    path(
        "logout/",
        auth_views.LogoutView.as_view(
            next_page=reverse_lazy("authentication:login")
        ),
        name="logout",
    ),
    path(
        "registration/", CustomRegistrationView.as_view(), name="registration"
    ),
    # ── Password reset (TOTP / Google Authenticator) ──────────────────────────
    path(
        "password_reset/",
        PasswordResetRequestView.as_view(),
        name="password_reset",
    ),
    path(
        "password_reset/totp/<str:uidb64>/",
        PasswordResetTOTPView.as_view(),
        name="password_reset_totp",
    ),
    path(
        "password_reset/change/<str:uidb64>/",
        PasswordResetChangeView.as_view(),
        name="password_reset_change",
    ),
    path(
        "password_reset/complete/",
        TemplateView.as_view(
            template_name="password_reset/password_reset_complete.html"
        ),
        name="password_reset_complete",
    ),
    # ── Registration confirmation ─────────────────────────────────────────────
    path(
        "registration/done/",
        TemplateView.as_view(
            template_name="registration/registration_done.html"
        ),
        name="registration_done",
    ),
    path(
        "registration/<uidb64>/<token>/",
        RegistrationCompleteView.as_view(),
        name="registration_complete",
    ),
]
