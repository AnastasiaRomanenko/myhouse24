from django.db import models


class PaymentReceiptStatus(models.TextChoices):
    PAID = "paid", "Opłacono"
    PARTIALLY_PAID = "partially paid", "Częściowo opłacono"
    NOT_PAID = "not_paid", "Nie opłacono"


class AccountingType(models.TextChoices):
    INCOME = "income", "Przychód"
    EXPENSE = "expense", "Wydatek"


class RequestStatus(models.TextChoices):
    NEW = "new", "Nowe"
    IN_PROGRESS = "in_progress", "W trakcie"
    DONE = "done", "Zakończono"


class MeterReadingStatus(models.TextChoices):
    NEW = "new", "Nowe"
    TAKEN_INTO_ACCOUNT = "taken_into_account", "Uwzględniono"
    TAKEN_INTO_ACCOUNT_AND_PAID = (
        "taken_into_account_and_Paid",
        "Uwzględniono i opłacono",
    )
    NULL = "null", "Zerowe"
