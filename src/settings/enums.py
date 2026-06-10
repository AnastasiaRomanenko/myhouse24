from django.db import models


class Type(models.TextChoices):
    INCOME = "income", "Przychód"
    EXPENSE = "expense", "Wydatek"
