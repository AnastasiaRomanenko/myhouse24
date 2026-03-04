from django.contrib.auth import views as auth_views
from django.urls import path, reverse_lazy
from django.views.generic import TemplateView

from src.authentication.forms import CustomSetPasswordForm
from src.authentication.views.login import CustomLoginView
from src.authentication.views.password_reset import CustomPasswordResetView
from src.authentication.views.registration import (
    CustomRegistrationView,
    RegistrationCompleteView,
)

app_name = "authentication"
urlpatterns = [
    path("", CustomLoginView.as_view(), name="login"),
    path(
        "logout/",
        auth_views.LogoutView.as_view(
            template_name="logout.html",
        ),
        name="logout",
    ),
    path(
        "registration/", CustomRegistrationView.as_view(), name="registration"
    ),
    path(
        "password_reset/",
        CustomPasswordResetView.as_view(),
        name="password_reset",
    ),
    path(
        "password_reset/done/",
        auth_views.PasswordResetDoneView.as_view(
            template_name="password_reset/password_reset_done.html"
        ),
        name="password_reset_done",
    ),
    path(
        "reset/<uidb64>/<token>/",
        auth_views.PasswordResetConfirmView.as_view(
            form_class=CustomSetPasswordForm,
            template_name="password_reset/password_reset_confirm.html",
            success_url=reverse_lazy("authentication:password_reset_complete"),
        ),
        name="password_reset_confirm",
    ),
    path(
        "reset/done/",
        auth_views.PasswordResetCompleteView.as_view(
            template_name="password_reset/password_reset_complete.html"
        ),
        name="password_reset_complete",
    ),
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
