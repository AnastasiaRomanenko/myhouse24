from django import forms
from django.contrib.auth import get_user_model
from django.contrib.auth.forms import SetPasswordForm

from src.users.enums import Status

Users = get_user_model()


class OwnerForm(forms.ModelForm):
    password1 = forms.CharField(
        required=False,
        widget=forms.PasswordInput(attrs={"class": "form-control"}),
    )
    password2 = forms.CharField(
        required=False,
        widget=forms.PasswordInput(attrs={"class": "form-control"}),
    )
    date_of_birth = forms.DateField(
        required=False,
        input_formats=["%d.%m.%Y", "%Y-%m-%d"],
        widget=forms.TextInput(
            attrs={
                "class": "form-control js-datepicker",
                "placeholder": "dd.mm.rrrr",
            }
        ),
    )

    class Meta:
        model = Users
        fields = [
            "image",
            "first_name",
            "last_name",
            "patronimic_name",
            "date_of_birth",
            "phone_number",
            "viber",
            "telegram",
            "email",
            "status",
            "external_id",
            "notes",
        ]
        widgets = {
            "image": forms.FileInput(attrs={"class": "form-control"}),
            "first_name": forms.TextInput(),
            "last_name": forms.TextInput(),
            "patronimic_name": forms.TextInput(),
            "date_of_birth": forms.TextInput(
                attrs={"class": "form-control js-datepicker"}
            ),
            "telegram": forms.TextInput(),
            "email": forms.EmailInput(),
            "status": forms.Select(
                choices=Status.choices, attrs={"class": "form-control"}
            ),
            "external_id": forms.NumberInput(),
            "notes": forms.Textarea(),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        if not self.instance or not self.instance.pk:
            self.fields["password1"].required = True
            self.fields["password2"].required = True

        if self.instance and self.instance.pk and self.instance.date_of_birth:
            self.initial["date_of_birth"] = (
                self.instance.date_of_birth.strftime("%d.%m.%Y")
            )

    def clean_email(self):
        email = self.cleaned_data.get("email")
        qs = Users.objects.filter(email=email)
        if self.instance and self.instance.pk:
            qs = qs.exclude(pk=self.instance.pk)
        if qs.exists():
            raise forms.ValidationError("User with this Email already exists.")
        return email

    def clean(self):
        cleaned_data = super().clean()
        password1 = cleaned_data.get("password1")
        password2 = cleaned_data.get("password2")

        if self.instance and self.instance.pk:
            if password1 or password2:
                if password1 != password2:
                    raise forms.ValidationError("Passwords don't match")
        else:
            if not password1 or not password2:
                raise forms.ValidationError("Password is required")
            if password1 != password2:
                raise forms.ValidationError("Passwords don't match")

        return cleaned_data

    def save(self, commit=True):
        owner = super().save(commit=False)
        password1 = self.cleaned_data.get("password1")

        if password1:
            owner.set_password(password1)

        if commit:
            owner.save()

        return owner


class UserForm(forms.ModelForm):
    password1 = forms.CharField(
        required=False,
        widget=forms.PasswordInput(attrs={"class": "form-control"}),
    )
    password2 = forms.CharField(
        required=False,
        widget=forms.PasswordInput(attrs={"class": "form-control"}),
    )

    class Meta:
        model = Users
        fields = [
            "last_name",
            "first_name",
            "email",
            "phone_number",
            "status",
            "role",
        ]
        widgets = {
            "last_name": forms.TextInput(attrs={"class": "form-control"}),
            "first_name": forms.TextInput(attrs={"class": "form-control"}),
            "email": forms.EmailInput(attrs={"class": "form-control"}),
            "status": forms.Select(choices=Status.choices),
            "role": forms.Select(choices=Status.choices),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        if not self.instance or not self.instance.pk:
            self.fields["password1"].required = True
            self.fields["password2"].required = True

    def clean_email(self):
        email = self.cleaned_data.get("email")
        qs = Users.objects.filter(email=email)
        if self.instance and self.instance.pk:
            qs = qs.exclude(pk=self.instance.pk)
        if qs.exists():
            raise forms.ValidationError("User with this Email already exists.")
        return email

    def clean(self):
        cleaned_data = super().clean()
        password1 = cleaned_data.get("password1")
        password2 = cleaned_data.get("password2")

        if self.instance and self.instance.pk:
            if password1 or password2:
                if password1 != password2:
                    raise forms.ValidationError("Passwords don't match")
        else:
            if not password1 or not password2:
                raise forms.ValidationError("Password is required")
            if password1 != password2:
                raise forms.ValidationError("Passwords don't match")

        return cleaned_data

    def save(self, commit=True):
        user = super().save(commit=False)
        password1 = self.cleaned_data.get("password1")

        if password1:
            user.set_password(password1)

        if commit:
            user.save()

        return user


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

    def save(self, commit=True):
        user = super().save(commit=False)
        password1 = self.cleaned_data.get("new_password1")

        if password1:
            user.set_password(password1)
            user.is_active = True

        if commit:
            user.save()

        return user


class OwnerInviteForm(forms.Form):
    email = forms.EmailField(
        widget=forms.EmailInput(attrs={"class": "form-control"})
    )
