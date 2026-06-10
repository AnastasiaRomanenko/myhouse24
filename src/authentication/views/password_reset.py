import base64
import io

import pyotp
import qrcode
from django.contrib.auth import get_user_model
from django.shortcuts import redirect, render
from django.utils.encoding import force_bytes, force_str
from django.utils.http import urlsafe_base64_decode, urlsafe_base64_encode
from django.views import View

from src.authentication.forms import (
    CustomSetPasswordForm,
    PasswordResetRequestForm,
)

Users = get_user_model()

# Session key used to mark that TOTP was successfully verified for a given uid.
_SESSION_KEY = "totp_reset_verified_uid"


def _uid_to_user(uidb64):
    """Decode uidb64 and return the Users instance, or None on any error."""
    try:
        uid = force_str(urlsafe_base64_decode(uidb64))
        return Users.objects.get(pk=uid)
    except (Users.DoesNotExist, ValueError, TypeError, OverflowError):
        return None


def _qr_data_uri(totp_uri: str) -> str:
    """Return a PNG data URI for the provisioning URI so it can be embedded in <img>."""
    img = qrcode.make(totp_uri)
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    b64 = base64.b64encode(buf.getvalue()).decode("ascii")
    return f"data:image/png;base64,{b64}"


class PasswordResetRequestView(View):
    """Step 1 — user enters their e-mail address."""

    template_name = "password_reset/password_reset_form.html"

    def get(self, request):
        return render(
            request, self.template_name, {"form": PasswordResetRequestForm()}
        )

    def post(self, request):
        form = PasswordResetRequestForm(request.POST)
        if not form.is_valid():
            return render(request, self.template_name, {"form": form})

        email = form.cleaned_data["email"]
        user = Users.objects.filter(email=email).first()
        if not user:
            # Show the same "check your authenticator" page to prevent email enumeration.
            return render(
                request,
                self.template_name,
                {
                    "form": form,
                    "email_not_found": True,
                },
            )

        # Generate (or reuse) a TOTP secret and persist it on the user.
        if not user.totp_secret:
            user.totp_secret = pyotp.random_base32()
            user.save(update_fields=["totp_secret"])

        uidb64 = urlsafe_base64_encode(force_bytes(user.pk))
        return redirect("authentication:password_reset_totp", uidb64=uidb64)


class PasswordResetTOTPView(View):
    """Step 2 — show QR code and ask user to enter the 6-digit TOTP code."""

    template_name = "password_reset/password_reset_totp.html"

    def _context(self, user, uidb64, error=None):
        totp = pyotp.TOTP(user.totp_secret)
        uri = totp.provisioning_uri(
            name=user.email,
            issuer_name="MyHouse24",
        )
        return {
            "qr_data_uri": _qr_data_uri(uri),
            "totp_secret": user.totp_secret,
            "uidb64": uidb64,
            "error": error,
        }

    def get(self, request, uidb64):
        user = _uid_to_user(uidb64)
        if not user or not user.totp_secret:
            return redirect("authentication:password_reset")
        return render(request, self.template_name, self._context(user, uidb64))

    def post(self, request, uidb64):
        user = _uid_to_user(uidb64)
        if not user or not user.totp_secret:
            return redirect("authentication:password_reset")

        code = request.POST.get("totp_code", "").strip()
        totp = pyotp.TOTP(user.totp_secret)

        if totp.verify(code, valid_window=1):
            # Store verification in the session so step 3 can trust it.
            request.session[_SESSION_KEY] = uidb64
            return redirect(
                "authentication:password_reset_change", uidb64=uidb64
            )

        return render(
            request,
            self.template_name,
            self._context(
                user, uidb64, error="Nieprawidłowy kod. Spróbuj ponownie."
            ),
        )


class PasswordResetChangeView(View):
    """Step 3 — set a new password (only accessible after TOTP verification)."""

    template_name = "password_reset/password_reset_confirm.html"

    def _get_verified_user(self, request, uidb64):
        if request.session.get(_SESSION_KEY) != uidb64:
            return None
        return _uid_to_user(uidb64)

    def get(self, request, uidb64):
        user = self._get_verified_user(request, uidb64)
        if not user:
            return redirect("authentication:password_reset")
        return render(
            request,
            self.template_name,
            {
                "form": CustomSetPasswordForm(user),
                "validlink": True,
            },
        )

    def post(self, request, uidb64):
        user = self._get_verified_user(request, uidb64)
        if not user:
            return redirect("authentication:password_reset")

        form = CustomSetPasswordForm(user, request.POST)
        if form.is_valid():
            form.save()
            # Invalidate the session marker so this link can't be reused.
            del request.session[_SESSION_KEY]
            return redirect("authentication:password_reset_complete")

        return render(
            request, self.template_name, {"form": form, "validlink": True}
        )
