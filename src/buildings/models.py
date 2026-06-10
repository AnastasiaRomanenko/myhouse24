from django.db import models

from src.settings.models import Tariffs
from src.users.models import Users


# Create your models here.
class Houses(models.Model):
    title = models.CharField(max_length=50)
    address = models.CharField(max_length=50)

    image1 = models.ImageField(upload_to="houses/", blank=True, null=True)
    image2 = models.ImageField(upload_to="houses/", blank=True, null=True)
    image3 = models.ImageField(upload_to="houses/", blank=True, null=True)
    image4 = models.ImageField(upload_to="houses/", blank=True, null=True)
    image5 = models.ImageField(upload_to="houses/", blank=True, null=True)

    workers = models.ManyToManyField(
        Users, blank=True, related_name="managed_houses"
    )

    def __str__(self) -> str:
        return self.title


class Floors(models.Model):
    title = models.CharField(max_length=50)
    house = models.ForeignKey(Houses, on_delete=models.CASCADE)

    def __str__(self) -> str:
        return f"{self.house}: {self.title}"


class Sections(models.Model):
    title = models.CharField(max_length=50)
    house = models.ForeignKey(Houses, on_delete=models.CASCADE)

    def __str__(self) -> str:
        return f"{self.house}: {self.title}"


class Flats(models.Model):
    number = models.PositiveSmallIntegerField()
    area = models.FloatField()

    section = models.ForeignKey(Sections, on_delete=models.PROTECT)
    floor = models.ForeignKey(Floors, on_delete=models.PROTECT)
    owner = models.ForeignKey(Users, on_delete=models.PROTECT)
    tariff = models.ForeignKey(Tariffs, on_delete=models.PROTECT)
    house = models.ForeignKey(Houses, on_delete=models.CASCADE)

    def __str__(self) -> str:
        return f"{self.house} / {self.number}"
