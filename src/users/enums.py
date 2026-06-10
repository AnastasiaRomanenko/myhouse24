from django.db import models


class Status(models.TextChoices):
    ACTIVE = "active", "Aktywny"
    INACTIVE = "inactive", "Nieaktywny"
    NEW = "new", "Nowy"
