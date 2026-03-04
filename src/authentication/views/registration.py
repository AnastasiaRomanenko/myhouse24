import requests
from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.auth.tokens import default_token_generator
from django.shortcuts import redirect, render
from django.template.loader import render_to_string
from django.urls import reverse_lazy
from django.utils.encoding import force_bytes, force_str
from django.utils.http import urlsafe_base64_decode, urlsafe_base64_encode
from django.views import View
from django.views.generic import CreateView

from src.authentication.forms import RegistrationForm
from src.authentication.tasks import send_bulk_emails
from src.users.enums import Status

Users = get_user_model()


class CustomRegistrationView(CreateView):
    form_class = RegistrationForm
    template_name = "registration/registration_form.html"
    subject_template_name = "registration/confirmation_subject.txt"
    email_template_name = "registration/confirmation_email.html"
    success_url = reverse_lazy("authentication:registration_done")

    def get(self, request, *args, **kwargs):
        return render(
            request,
            self.template_name,
            {
                "form": self.form_class(),
                "site_key": settings.RECAPTCHA_SITE_KEY,
            },
        )

    def post(self, request, *args, **kwargs):
        # reCAPTCHA v2 checkbox
        recaptcha_response = request.POST.get("g-recaptcha-response", "")
        verify = requests.post(
            "https://www.google.com/recaptcha/api/siteverify",
            data={
                "secret": settings.RECAPTCHA_SECRET_KEY,
                "response": recaptcha_response,
                "remoteip": request.META.get("REMOTE_ADDR"),
            },
            timeout=5,
        ).json()

        if not verify.get("success"):
            return render(
                request,
                self.template_name,
                {
                    "form": self.form_class(),
                    "site_key": settings.RECAPTCHA_SITE_KEY,
                },
            )

        form = self.form_class(request.POST)
        if not form.is_valid():
            return render(
                request,
                self.template_name,
                {
                    "form": form,
                    "site_key": settings.RECAPTCHA_SITE_KEY,
                },
            )
        user = form.save(commit=False)
        user.is_active = False
        user.status = Status.NEW
        user.save()

        uidb64 = urlsafe_base64_encode(force_bytes(user.pk))
        token = default_token_generator.make_token(user)

        subject = "Подтвердить аккаунт"

        body = render_to_string(
            self.email_template_name,
            {
                "user": user,
                "token": token,
                "uid": uidb64,
                "protocol": "https" if request.is_secure() else "http",
                "domain": request.get_host(),
            },
        )

        send_bulk_emails.delay(subject, body, user.email)
        return redirect("authentication:registration_done")


class RegistrationCompleteView(View):
    template_name = "registration/registration_complete.html"
    invalid_template_name = "registration/registration_invalid.html"

    def get_user_from_uid(self, uidb64):
        try:
            uid = force_str(urlsafe_base64_decode(uidb64))
            return Users.objects.get(pk=uid, is_active=True)
        except Exception:
            return None

    def get(self, request, uidb64, token):
        try:
            uid = force_str(urlsafe_base64_decode(uidb64))
            user = Users.objects.get(pk=uid, is_active=False)
        except (Users.DoesNotExist, ValueError, TypeError):
            user = None

        if user and default_token_generator.check_token(user, token):
            user.is_active = True
            user.save()
            return render(request, self.template_name)
        else:
            return render(request, self.invalid_template_name)
