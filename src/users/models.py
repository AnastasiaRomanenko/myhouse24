from django.contrib.auth.models import AbstractUser
from django.db import models
from phonenumber_field.modelfields import PhoneNumberField

from src.users.enums import Status
from src.users.managers import UserManager


# Create your models here.
class Roles(models.Model):
    role = models.CharField(max_length=50)

    has_statistics = models.BooleanField(default=False)
    has_cash_register = models.BooleanField(default=False)
    has_payment_receipts = models.BooleanField(default=False)
    has_bank_books = models.BooleanField(default=False)
    has_flats = models.BooleanField(default=False)
    has_flats_owners = models.BooleanField(default=False)
    has_houses = models.BooleanField(default=False)
    has_messages = models.BooleanField(default=False)
    has_requests = models.BooleanField(default=False)
    has_meter_readings = models.BooleanField(default=False)
    has_site_management = models.BooleanField(default=False)
    has_services = models.BooleanField(default=False)
    has_tariffs = models.BooleanField(default=False)
    has_roles = models.BooleanField(default=False)
    has_users = models.BooleanField(default=False)
    has_payment_details = models.BooleanField(default=False)
    has_payment_items = models.BooleanField(default=False)

    def __str__(self) -> str:
        return self.role


class Users(AbstractUser):

    username = None
    is_active = models.BooleanField(default=False)

    image = models.ImageField(upload_to="users/", blank=True, null=True)

    patronimic_name = models.CharField(max_length=50, null=True, blank=True)
    date_of_birth = models.DateField(null=True, blank=True)

    external_id = models.PositiveIntegerField(null=True, blank=True)

    status = models.CharField(
        max_length=16,
        choices=Status.choices,
        default=Status.NEW,
    )

    notes = models.TextField(blank=True, null=True)

    phone_number = PhoneNumberField(null=True, blank=True)
    viber = PhoneNumberField(null=True, blank=True)
    telegram = models.CharField(max_length=50, blank=True, null=True)

    email = models.EmailField(unique=True)

    totp_secret = models.CharField(max_length=64, blank=True, null=True)

    role = models.ForeignKey(
        Roles,
        on_delete=models.SET_NULL,
        related_name="users",
        null=True,
        blank=True,
    )
    objects = UserManager()

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = []

    def __str__(self):
        return self.email
