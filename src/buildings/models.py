from django.db import models

from src.settings.models import Tariffs
from src.users.models import Users


# Create your models here.
class Houses(models.Model):
    title = models.CharField(max_length=50)
    address = models.CharField(max_length=50)

    image1 = models.ImageField(upload_to="houses/")
    image2 = models.ImageField(upload_to="houses/")
    image3 = models.ImageField(upload_to="houses/")
    image4 = models.ImageField(upload_to="houses/")
    image5 = models.ImageField(upload_to="houses/")

    workers = models.ManyToManyField(Users, related_name="houses", blank=True)

    def __str__(self) -> str:
        return self.title


class Floors(models.Model):
    title = models.CharField(max_length=50)
    house = models.ForeignKey(
        Houses, on_delete=models.CASCADE, related_name="floors"
    )

    def __str__(self) -> str:
        return f"{self.house}: {self.title}"


class Sections(models.Model):
    title = models.CharField(max_length=50)
    house = models.ForeignKey(
        Houses, on_delete=models.CASCADE, related_name="sections"
    )

    def __str__(self) -> str:
        return f"{self.house}: {self.title}"


class Flats(models.Model):
    number = models.PositiveSmallIntegerField()
    area = models.FloatField()

    section = models.ForeignKey(
        Sections, on_delete=models.PROTECT, related_name="flats"
    )
    floor = models.ForeignKey(
        Floors, on_delete=models.PROTECT, related_name="flats"
    )
    owner = models.ForeignKey(
        Users, on_delete=models.PROTECT, related_name="owned_flats"
    )
    tariff = models.ForeignKey(
        Tariffs, on_delete=models.PROTECT, related_name="flats"
    )
    house = models.ForeignKey(
        Houses, on_delete=models.CASCADE, related_name="flats"
    )

    def __str__(self) -> str:
        return f"{self.house} / {self.number}"
