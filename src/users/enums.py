from django.db import models


class Status(models.TextChoices):
    ACTIVE = "active", "Активен"
    INACTIVE = "inactive", "Отлючен"
    NEW = "new", "Новый"
