from django.db import models

from src.settings.enums import Type


# Create your models here.
class UnitsOfMeasurement(models.Model):
    title = models.CharField(max_length=50)

    def __str__(self) -> str:
        return self.title


class Tariffs(models.Model):
    title = models.CharField(max_length=50)
    description = models.TextField()
    update_at = models.DateTimeField()

    def __str__(self) -> str:
        return self.title


class Services(models.Model):
    title = models.CharField(max_length=50)
    unit_of_measurement = models.ForeignKey(
        UnitsOfMeasurement, on_delete=models.PROTECT, related_name="services"
    )
    show = models.BooleanField(default=True)

    def __str__(self) -> str:
        return self.title


class ServiceTariffs(models.Model):
    service = models.ForeignKey(
        Services, on_delete=models.CASCADE, related_name="service_tariffs"
    )
    tariff = models.ForeignKey(
        Tariffs, on_delete=models.CASCADE, related_name="service_tariffs"
    )
    price = models.FloatField()

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["service", "tariff"], name="uniq_service_tariff"
            )
        ]

    def __str__(self) -> str:
        return f"{self.service} / {self.tariff}"


class PaymentDetails(models.Model):
    company_name = models.CharField(max_length=50)
    information = models.TextField()

    def __str__(self) -> str:
        return self.company_name


class PaymentItems(models.Model):

    name = models.CharField(max_length=50)
    type = models.CharField(max_length=32, choices=Type.choices)

    def __str__(self) -> str:
        return self.name
