from django.db import models
from django.contrib.auth.models import AbstractUser
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

    def __str__(self) -> str:
        return self.role


class Users(AbstractUser):

    username = None

    image = models.ImageField(upload_to="users/", blank=True, null=True)

    patronimic_name = models.CharField(max_length=50, null=True, blank=True)
    date_of_birth = models.DateField(null=True, blank=True)

    external_id = models.PositiveIntegerField(null=True, blank=True)

    status = models.CharField(
        max_length=16,
        choices=Status.choices,
        default=Status.ACTIVE,
    )

    notes = models.TextField(blank=True)

    phone_number = PhoneNumberField(max_length=32, blank=True, null=True)
    viber = PhoneNumberField(max_length=32, blank=True, null=True)
    telegram = models.CharField(max_length=50, blank=True, null=True)

    email = models.EmailField(unique=True)

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