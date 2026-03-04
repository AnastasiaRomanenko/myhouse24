from django import forms
from phonenumber_field.phonenumber import PhoneNumber

from src.users.models import Users


class AdminForms(forms.ModelForm):
    password = forms.CharField(
        label="Пароль",
        widget=forms.PasswordInput(attrs={"class": "form-control"}),
        required=False,
    )
    repeat_password = forms.CharField(
        label="Повторить пароль",
        widget=forms.PasswordInput(attrs={"class": "form-control"}),
        required=False,
    )

    class Meta:
        model = Users
        fields = ["first_name", "last_name", "phone_number", "email"]
        widgets = {
            "first_name": forms.TextInput(attrs={"class": "form-control"}),
            "last_name": forms.TextInput(attrs={"class": "form-control"}),
            "phone_number": PhoneNumber(),
            "email": forms.EmailInput(attrs={"class": "form-control"}),
        }

    def clean(self):
        cleaned = super().clean()
        p1 = cleaned.get("password")
        p2 = cleaned.get("repeat_password")

        if p1 or p2:
            if not p1 or not p2:
                raise forms.ValidationError("Введите оба пароля.")
            if p1 != p2:
                raise forms.ValidationError("Пароли не совпадают.")
        return cleaned

    def save(self, commit=True):
        user = super().save(commit=False)

        p1 = self.cleaned_data.get("password")
        if p1:
            user.set_password(p1)

        if commit:
            user.save()
        return user
