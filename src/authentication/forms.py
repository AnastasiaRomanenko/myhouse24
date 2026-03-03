from django import forms
from django.contrib.auth import authenticate, get_user_model
from email_validator import validate_email, EmailNotValidError
from django.contrib.auth.forms import UserCreationForm, SetPasswordForm


Users = get_user_model()


class RegistrationForm(UserCreationForm):
    password1 = forms.CharField(
        widget=forms.PasswordInput(attrs={"class": "form-control", "placeholder": "Пароль", "required": True}),
    )
    password2 = forms.CharField(
        widget=forms.PasswordInput(attrs={"class": "form-control", "placeholder": "Повторить пароль", "required": True}),
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
            "first_name": forms.TextInput(attrs={"class": "form-control", "placeholder": "Имя", "required": True}),
            "last_name": forms.TextInput(attrs={"class": "form-control", "placeholder": "Фамилия", "required": True}),
            "email": forms.EmailInput(attrs={"class": "form-control", "placeholder": "Почта", "required": True}),
        }

    # def clean(self):
    #     password1 = self.cleaned_data.get("password1")
    #     password2 = self.cleaned_data.get("password2")
    #     if password1 and password2 and password1 != password2:
    #         raise forms.ValidationError("Пароли не совпадают.")
    #     return self.cleaned_data

    def clean_email(self):
        email = self.cleaned_data["email"]
        if Users.objects.filter(email=email).exists():
            raise forms.ValidationError("Почта уже существует. Выберите другую.")
        return email


class UserLoginForm(forms.Form):
    login = forms.CharField(
        widget=forms.TextInput(attrs={"class": "form-control", "placeholder": "Почта или ID", "required": True})
    )
    password = forms.CharField(
        widget=forms.PasswordInput(attrs={"class": "form-control", "placeholder": "Пароль", "required": True})
    )

    def clean(self):
        login = self.cleaned_data.get("login")
        password = self.cleaned_data.get("password")

        if not login or not password:
            return self.cleaned_data

        # ID
        if login.isdecimal():
            user = authenticate(external_id=login, password=password)  # IDAuthBackend
            if not user:
                raise forms.ValidationError("Неправильный ID или пароль.")
            self.cleaned_data["user"] = user
            return self.cleaned_data

        # Email
        try:
            validate_email(login)
        except EmailNotValidError:
            raise forms.ValidationError("Неправильная почта или ID.")

        user = authenticate(email=login, password=password)  # EmailAuthBackend
        if not user:
            raise forms.ValidationError("Неправильная почта или пароль.")

        self.cleaned_data["user"] = user
        return self.cleaned_data


class AdminLoginForm(forms.Form):
    login = forms.EmailField(
        widget=forms.EmailInput(attrs={"class": "form-control", "placeholder": "Почта", "required": True})
    )
    password = forms.CharField(
        widget=forms.PasswordInput(attrs={"class": "form-control", "placeholder": "Пароль", "required": True})
    )

    def clean(self):
        email = self.cleaned_data.get("login")
        password = self.cleaned_data.get("password")

        if not email or not password:
            return self.cleaned_data

        user = authenticate(email=email, password=password)  # EmailAuthBackend
        if not user:
            raise forms.ValidationError("Неправильная почта или пароль.")

        if not getattr(user, "is_staff", False):
            raise forms.ValidationError("Нет прав администратора.")

        self.cleaned_data["user"] = user
        return self.cleaned_data

class PasswordResetRequestForm(forms.Form):
    email = forms.EmailField(
        widget=forms.EmailInput(attrs={"class": "form-control", "placeholder": "Email", "required": True})
    )
    def clean_email(self):
        email = self.cleaned_data["email"].strip()
        return email

class CustomSetPasswordForm(SetPasswordForm):
    new_password1 = (forms.CharField(
        widget=forms.PasswordInput(attrs={"class": "form-control", "placeholder": "Пароль", "required": True}))
    )
    new_password2 = (forms.CharField(
        widget=forms.PasswordInput(attrs={"class": "form-control", "placeholder": "Повторить пароль", "required": True}))
    )


