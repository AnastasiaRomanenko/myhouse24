from django.db import models

class Type(models.TextChoices):
    INCOME = "income", "Приход"
    EXPENSE = "expense", "Расход"