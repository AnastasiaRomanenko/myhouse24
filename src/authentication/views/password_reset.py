from django.contrib.auth import get_user_model
from django.contrib.auth.tokens import default_token_generator
from django.shortcuts import redirect, render
from django.template.loader import render_to_string
from django.utils.http import urlsafe_base64_encode
from django.utils.encoding import force_bytes
from src.authentication.tasks import send_bulk_emails
from src.authentication.forms import PasswordResetRequestForm
from django.contrib.auth.views import PasswordResetView

Users = get_user_model()

class CustomPasswordResetView(PasswordResetView):
    form_class = PasswordResetRequestForm
    template_name = "password_reset/password_reset_form.html"
    subject_template_name = "password_reset/password_reset_subject.txt"
    email_template_name = "password_reset/password_reset_email.html"

    def get(self, request, *args, **kwargs):
        return render(request, self.template_name, {"form": self.form_class()})

    def post(self, request, *args, **kwargs):
        form = self.form_class(request.POST)
        if not form.is_valid():
            return render(request, self.template_name, {"form": form})

        email = form.cleaned_data["email"]
        user = Users.objects.get(email=email)

        if user:
            uidb64 = urlsafe_base64_encode(force_bytes(user.pk))
            token = default_token_generator.make_token(user)

            body = render_to_string(self.email_template_name, {
                "user": user,
                "token": token,
                "uid": uidb64,
                "protocol": "https" if request.is_secure() else "http",
                "domain": request.get_host(),
            }).strip().replace("\n", "")

            send_bulk_emails.delay(self.subject_template_name, body, email)
            return redirect("authentication:password_reset_done")

        return render(request, self.template_name, {"form": form})