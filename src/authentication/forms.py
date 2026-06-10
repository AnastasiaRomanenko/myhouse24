from django import forms
from django.contrib.auth import authenticate, get_user_model
from django.contrib.auth.forms import SetPasswordForm, UserCreationForm
from email_validator import EmailNotValidError, validate_email

Users = get_user_model()


class RegistrationForm(UserCreationForm):
    password1 = forms.CharField(
        widget=forms.PasswordInput(
            attrs={
                "class": "form-control",
                "placeholder": "Hasło",
                "required": True,
            }
        ),
    )
    password2 = forms.CharField(
        widget=forms.PasswordInput(
            attrs={
                "class": "form-control",
                "placeholder": "Powtórz hasło",
                "required": True,
            }
        ),
    )
    accept_terms_and_conditions = forms.BooleanField(
        widget=forms.CheckboxInput(
            attrs={
                "class": "form-control",
                "type": "checkbox",
                "name": "accept_terms_and_conditions",
                "required": True,
            }
        ),
    )

    class Meta:
        model = Users
        fields = ["first_name", "last_name", "email"]
        widgets = {
            "first_name": forms.TextInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "Imię",
                    "required": True,
                }
            ),
            "last_name": forms.TextInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "Nazwisko",
                    "required": True,
                }
            ),
            "email": forms.EmailInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "E-mail",
                    "required": True,
                }
            ),
        }

    def clean_email(self):
        email = self.cleaned_data["email"]
        if Users.objects.filter(email=email).exists():
            raise forms.ValidationError(
                "Ten adres e-mail jest już zajęty. Wybierz inny."
            )
        return email


class UserLoginForm(forms.Form):
    login = forms.CharField(
        widget=forms.TextInput(
            attrs={
                "class": "form-control",
                "placeholder": "E-mail lub ID",
                "required": True,
            }
        )
    )
    password = forms.CharField(
        widget=forms.PasswordInput(
            attrs={
                "class": "form-control",
                "placeholder": "Hasło",
                "required": True,
            }
        )
    )

    def clean(self):
        login = self.cleaned_data.get("login")
        password = self.cleaned_data.get("password")

        if not login or not password:
            return self.cleaned_data

        # ID
        if login.isdecimal():
            user = authenticate(
                external_id=login, password=password
            )  # IDAuthBackend
            if not user:
                raise forms.ValidationError(
                    "Nieprawidłowy identyfikator lub hasło."
                )
            self.cleaned_data["user"] = user
            return self.cleaned_data

        # Email
        try:
            validate_email(login)
        except EmailNotValidError:
            raise forms.ValidationError(
                "Nieprawidłowy adres e-mail lub identyfikator."
            )

        user = authenticate(email=login, password=password)  # EmailAuthBackend
        if not user:
            raise forms.ValidationError(
                "Nieprawidłowy adres e-mail lub hasło."
            )

        self.cleaned_data["user"] = user
        return self.cleaned_data


class AdminLoginForm(forms.Form):
    login = forms.EmailField(
        widget=forms.EmailInput(
            attrs={
                "class": "form-control",
                "placeholder": "E-mail",
                "required": True,
            }
        )
    )
    password = forms.CharField(
        widget=forms.PasswordInput(
            attrs={
                "class": "form-control",
                "placeholder": "Hasło",
                "required": True,
            }
        )
    )

    def clean(self):
        email = self.cleaned_data.get("login")
        password = self.cleaned_data.get("password")

        if not email or not password:
            return self.cleaned_data

        user = authenticate(email=email, password=password)  # EmailAuthBackend
        if not user:
            raise forms.ValidationError(
                "Nieprawidłowy adres e-mail lub hasło."
            )

        if not getattr(user, "is_staff", False):
            raise forms.ValidationError("Brak uprawnień administratora.")

        self.cleaned_data["user"] = user
        return self.cleaned_data


class PasswordResetRequestForm(forms.Form):
    email = forms.EmailField(
        widget=forms.EmailInput(
            attrs={
                "class": "form-control",
                "placeholder": "E-mail",
                "required": True,
            }
        )
    )

    def clean_email(self):
        email = self.cleaned_data["email"].strip()
        return email


class CustomSetPasswordForm(SetPasswordForm):
    new_password1 = forms.CharField(
        widget=forms.PasswordInput(
            attrs={
                "class": "form-control",
                "placeholder": "Hasło",
                "required": True,
            }
        )
    )
    new_password2 = forms.CharField(
        widget=forms.PasswordInput(
            attrs={
                "class": "form-control",
                "placeholder": "Powtórz hasło",
                "required": True,
            }
        )
    )
