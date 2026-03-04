from django.db import models


class PaymentReceiptStatus(models.TextChoices):
    PAID = "paid", "Оплачено"
    PARTIALLY_PAID = "partially paid", "Частично оплачено"
    NOT_PAID = "not_paid", "Не оплачено"


class AccountingType(models.TextChoices):
    INCOME = "income", "Приход"
    EXPENSE = "expense", "Расход"


class RequestStatus(models.TextChoices):
    NEW = "new", "Новое"
    IN_PROGRESS = "in_progress", "В работе"
    DONE = "done", "Выполнено"


class MeterReadingStatus(models.TextChoices):
    NEW = "new", "Новое"
    TAKEN_INTO_ACCOUNT = "taken_into_account", "Учтено"
    TAKEN_INTO_ACCOUNT_AND_PAID = (
        "taken_into_account_and_Paid",
        "Учтено и оплачено",
    )
    NULL = "null", "Нулевое"
