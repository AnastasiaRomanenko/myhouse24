from django import forms
from django.contrib.auth.backends import ModelBackend
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth import get_user_model

Users = get_user_model()


class EmailAuthBackend(ModelBackend):
    """Authenticate users using their email address instead of a username."""

    def authenticate(self, request, username=None, password=None, **kwargs):
        try:
            user = Users.objects.get(email=username)
            if user.check_password(password):
                return user
        except Users.DoesNotExist:
            return None

    def get_user(self, user_id):
        """Retrieve a user by their ID."""
        try:
            return Users.objects.get(pk=user_id)
        except Users.DoesNotExist:
            return None


class IDAuthBackend(ModelBackend):
    """Authenticate users using their external_id instead of a username (not applicable for admin)."""

    def authenticate(self, request, username=None, password=None, **kwargs):
        try:
            user = Users.objects.get(external_id=username)
            if user.check_password(password):
                return user
        except Users.DoesNotExist:
            return None

    def get_user(self, user_id):
        """Retrieve a user by their ID."""
        try:
            return Users.objects.get(pk=user_id)
        except Users.DoesNotExist:
            return None