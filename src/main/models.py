from django.db import models
from phonenumber_field.modelfields import PhoneNumberField

# Create your models here.


class SEO(models.Model):
    title = models.CharField(max_length=50)
    description = models.TextField()
    keywords = models.CharField(max_length=50)

    def __str__(self) -> str:
        return self.title


class Images(models.Model):
    image = models.ImageField(upload_to="images/")

    def __str__(self) -> str:
        return f"Image #{self.pk}"


class Documents(models.Model):
    title = models.CharField(max_length=50)
    document = models.FileField(upload_to="documents/")

    def __str__(self) -> str:
        return self.title


class Blocks(models.Model):
    image = models.ImageField(upload_to="blocks/")
    title = models.CharField(max_length=50)
    description = models.TextField()

    def __str__(self) -> str:
        return self.title


class SiteServices(models.Model):
    image = models.ImageField(upload_to="site_services/")
    title = models.CharField(max_length=50)
    description = models.TextField()

    def __str__(self) -> str:
        return self.title


class MainPage(models.Model):
    slide1 = models.ImageField(upload_to="main/slides/")
    slide2 = models.ImageField(upload_to="main/slides/")
    slide3 = models.ImageField(upload_to="main/slides/")
    title = models.CharField(max_length=50)
    description = models.TextField()

    block = models.ManyToManyField(
        Blocks, related_name="main_pages", blank=True
    )
    seo = models.OneToOneField(
        SEO, on_delete=models.CASCADE, related_name="main_page"
    )

    def __str__(self) -> str:
        return f"MainPage #{self.pk}"


class AboutUsPage(models.Model):
    director_photo = models.ImageField(upload_to="about/")
    title = models.CharField(max_length=50)
    description = models.TextField()

    gallery = models.ManyToManyField(
        Images, related_name="about_gallery_pages", blank=True
    )

    addtional_title = models.CharField(max_length=50)
    addtional_description = models.TextField()
    additional_gallery = models.ManyToManyField(
        Images, related_name="about_additional_gallery_pages", blank=True
    )

    documents = models.ManyToManyField(
        Documents, related_name="about_pages", blank=True
    )

    seo = models.OneToOneField(
        SEO, on_delete=models.CASCADE, related_name="about_page"
    )

    def __str__(self) -> str:
        return f"AboutUsPage #{self.pk}"


class ServicePage(models.Model):
    service = models.ManyToManyField(
        SiteServices, related_name="service_pages", blank=True
    )
    seo = models.OneToOneField(
        SEO, on_delete=models.CASCADE, related_name="service_page"
    )

    def __str__(self) -> str:
        return f"ServicePage #{self.pk}"


class ContactPage(models.Model):
    title = models.CharField(max_length=50)
    description = models.TextField()
    ceo_name = models.CharField(max_length=50)
    location = models.CharField(max_length=50)
    address = models.CharField(max_length=50)

    phone_number = PhoneNumberField(max_length=32)
    email = models.EmailField()
    web_page_url = models.URLField()
    map_url = models.URLField()

    seo = models.OneToOneField(
        SEO, on_delete=models.CASCADE, related_name="contact_page"
    )

    def __str__(self) -> str:
        return f"ContactPage #{self.pk}"
