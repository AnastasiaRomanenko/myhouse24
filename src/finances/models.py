from django.db import models

from src.buildings.models import Flats
from src.finances.enums import (
    AccountingType,
    MeterReadingStatus,
    PaymentReceiptStatus,
    RequestStatus,
)
from src.settings.models import PaymentItems, Services, Tariffs
from src.users.models import Users


# Create your models here.
class BankBook(models.Model):
    status = models.BooleanField(default=False)
    flat = models.OneToOneField(
        Flats, on_delete=models.CASCADE, related_name="bank_book"
    )
    random_number = models.CharField(max_length=11)

    def __str__(self) -> str:
        return f"BankBook {self.random_number}"


class PaymentReceipt(models.Model):
    random_number = models.CharField(max_length=11)
    date_from = models.DateField()

    flat = models.ForeignKey(
        Flats, on_delete=models.CASCADE, related_name="payment_receipts"
    )

    completed = models.BooleanField(default=False)
    status = models.CharField(
        max_length=16, choices=PaymentReceiptStatus.choices
    )

    tariff = models.ForeignKey(
        Tariffs, on_delete=models.PROTECT, related_name="payment_receipts"
    )

    period_from = models.DateField()
    period_to = models.DateField()

    bank_book = models.ForeignKey(
        BankBook, on_delete=models.PROTECT, related_name="payment_receipts"
    )

    def __str__(self) -> str:
        return f"Receipt {self.random_number}"


class PaymentReceiptService(models.Model):
    service = models.ForeignKey(
        Services, on_delete=models.PROTECT, related_name="receipt_lines"
    )
    payment_receipt = models.ForeignKey(
        PaymentReceipt, on_delete=models.CASCADE, related_name="lines"
    )
    price = models.FloatField()
    amount = models.PositiveSmallIntegerField()

    def __str__(self) -> str:
        return f"{self.payment_receipt} / {self.service}"


class Accounting(models.Model):
    type = models.CharField(max_length=16, choices=AccountingType.choices)

    payment_item = models.ForeignKey(
        PaymentItems, on_delete=models.PROTECT, related_name="accounting_rows"
    )
    owner = models.ForeignKey(
        Users, on_delete=models.PROTECT, related_name="accounting_owner_rows"
    )
    bank_book = models.ForeignKey(
        BankBook, on_delete=models.PROTECT, related_name="accounting_rows"
    )
    manager = models.ForeignKey(
        Users, on_delete=models.PROTECT, related_name="accounting_manager_rows"
    )

    random_number = models.CharField(max_length=11)
    amount = models.FloatField()

    created_at = models.DateField()
    completed = models.BooleanField(default=False)

    comment = models.TextField(blank=True)

    def __str__(self) -> str:
        return f"Accounting {self.random_number}"


class Message(models.Model):
    title = models.CharField(max_length=50)
    description = models.TextField()
    flat = models.ForeignKey(
        Flats, on_delete=models.CASCADE, related_name="messages"
    )
    to_debtors = models.BooleanField(default=False)

    def __str__(self) -> str:
        return self.title


class Request(models.Model):
    description = models.TextField()
    status = models.CharField(max_length=16, choices=RequestStatus.choices)

    flat = models.ForeignKey(
        Flats, on_delete=models.CASCADE, related_name="requests"
    )
    comment = models.TextField(blank=True)
    date_time = models.DateTimeField()

    def __str__(self) -> str:
        return f"Request #{self.pk}"


class MeterReading(models.Model):
    current_data = models.FloatField()
    meter_type = models.ForeignKey(
        Services, on_delete=models.PROTECT, related_name="meter_readings"
    )
    flat = models.ForeignKey(
        Flats, on_delete=models.CASCADE, related_name="meter_readings"
    )

    status = models.CharField(
        max_length=27, choices=MeterReadingStatus.choices
    )
    random_number = models.CharField(max_length=11)

    created_at = models.DateField()

    def __str__(self) -> str:
        return f"MeterReading {self.random_number}"
