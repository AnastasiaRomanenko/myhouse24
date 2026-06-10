import os

from django.contrib.auth import get_user_model
from django.core.files.base import ContentFile
from django.core.management.base import BaseCommand

import config.settings as settings
from src.buildings.models import Flats, Floors, Houses, Sections
from src.main.models import (
    SEO,
    AboutUsPage,
    ContactPage,
    MainPage,
    ServicePage,
)
from src.settings.enums import Type
from src.settings.models import (
    PaymentDetails,
    PaymentItems,
    Services,
    ServiceTariffs,
    Tariffs,
    UnitsOfMeasurement,
)
from src.users.enums import Status
from src.users.models import Roles

Users = get_user_model()


class Command(BaseCommand):
    help = "Initialize database with sample data for development/testing"

    def __init__(self):
        super().__init__()
        self.base_path = os.path.join(settings.BASE_DIR, "gallery")

    def add_arguments(self, parser):
        parser.add_argument(
            "--clear",
            action="store_true",
            help="Clear existing data before initialization",
        )

    def get_image_file(self, image_path):
        full_path = os.path.join(self.base_path, image_path)
        self.stdout.write(self.style.WARNING(full_path))
        try:
            with open(full_path, "rb") as f:
                return ContentFile(f.read(), name=os.path.basename(image_path))
        except FileNotFoundError:
            self.stdout.write(
                self.style.WARNING(f"Image not found: {full_path}")
            )

    def handle(self, *args, **options):
        if options["clear"]:
            self.stdout.write(self.style.WARNING("Clearing existing data..."))
            self.clear_data()

        self.stdout.write(
            self.style.SUCCESS("Starting database initialization...")
        )

        # Create data in order of dependencies
        self.create_roles()

        self.stdout.write(
            self.style.SUCCESS("Database initialization completed!")
        )

    def clear_data(self):
        models_to_clear = [Users]

        for model in models_to_clear:
            count = model.objects.count()
            model.objects.all().delete()
            self.stdout.write(f"  Deleted {count} {model.__name__} objects")

        Users.objects.filter(is_staff=False, is_superuser=False).delete()

    def create_staff(self, email, password, role, first_name):
        if not Users.objects.filter(email=email).exists():
            Users.objects.create_user(
                email=email,
                password=password,
                first_name=first_name,
                last_name="User",
                phone_number="+380931234567",
                role=role,
                is_staff=True,
                is_active=True,
                status=Status.ACTIVE,
            )
            self.stdout.write(self.style.SUCCESS(f"  Created {email}"))

    def create_roles(self):
        if not Roles.objects.filter(role="Dyrektor").exists():
            director_role = Roles.objects.create(
                role="Dyrektor",
                has_statistics=True,
                has_cash_register=True,
                has_payment_receipts=True,
                has_bank_books=True,
                has_flats=True,
                has_flats_owners=True,
                has_houses=True,
                has_messages=True,
                has_requests=True,
                has_meter_readings=True,
                has_site_management=True,
                has_services=True,
                has_tariffs=True,
                has_roles=True,
                has_users=True,
                has_payment_details=True,
                has_payment_items=True,
            )
            self.stdout.write(
                self.style.SUCCESS("  Created role for superuser (director)")
            )

            if not Users.objects.filter(email="admin@gmail.com").exists():
                Users.objects.create_superuser(
                    email="admin@gmail.com",
                    password="admin123",
                    first_name="Admin",
                    last_name="User",
                    phone_number="+380931234567",
                    role=director_role,
                    is_staff=True,
                    is_superuser=True,
                    status=Status.ACTIVE,
                )
                self.stdout.write(
                    self.style.SUCCESS(
                        "  Created superuser (admin@gmail.com/admin123)"
                    )
                )

        if not Roles.objects.filter(role="Zarządca").exists():
            manager_role = Roles.objects.create(
                role="Zarządca",
                has_statistics=True,
                has_cash_register=True,
                has_payment_receipts=True,
                has_bank_books=True,
                has_flats=True,
                has_flats_owners=True,
                has_houses=True,
                has_messages=True,
                has_requests=True,
                has_meter_readings=True,
                has_site_management=False,
                has_services=False,
                has_tariffs=False,
                has_roles=False,
                has_users=False,
                has_payment_details=False,
                has_payment_items=False,
            )
            self.stdout.write(
                self.style.SUCCESS("  Created role for staff (manager)")
            )
            self.create_staff(
                "manager@gmail.com", "admin123", manager_role, "Manager"
            )

        if not Roles.objects.filter(role="Księgowy").exists():
            accountant_role = Roles.objects.create(
                role="Księgowy",
                has_statistics=True,
                has_cash_register=True,
                has_payment_receipts=True,
                has_bank_books=True,
                has_flats=False,
                has_flats_owners=False,
                has_houses=False,
                has_messages=False,
                has_requests=False,
                has_meter_readings=False,
                has_site_management=False,
                has_services=False,
                has_tariffs=False,
                has_roles=False,
                has_users=False,
                has_payment_details=True,
                has_payment_items=False,
            )
            self.stdout.write(
                self.style.SUCCESS("  Created role for staff (accountant)")
            )
            self.create_staff(
                "accountant@gmail.com",
                "admin123",
                accountant_role,
                "Accountant",
            )

        if not Roles.objects.filter(role="Elektryk").exists():
            electrician_role = Roles.objects.create(
                role="Elektryk",
                has_statistics=False,
                has_cash_register=False,
                has_payment_receipts=False,
                has_bank_books=False,
                has_flats=True,
                has_flats_owners=True,
                has_houses=True,
                has_messages=True,
                has_requests=True,
                has_meter_readings=True,
                has_site_management=False,
                has_services=False,
                has_tariffs=False,
                has_roles=False,
                has_users=False,
                has_payment_details=False,
                has_payment_items=False,
            )
            self.stdout.write(
                self.style.SUCCESS("  Created role for staff (electrician)")
            )
            self.create_staff(
                "electrician@gmail.com",
                "admin123",
                electrician_role,
                "Electrician",
            )

        if not Roles.objects.filter(role="Hydraulik").exists():
            plumber_role = Roles.objects.create(
                role="Hydraulik",
                has_statistics=False,
                has_cash_register=False,
                has_payment_receipts=False,
                has_bank_books=False,
                has_flats=True,
                has_flats_owners=True,
                has_houses=True,
                has_messages=True,
                has_requests=True,
                has_meter_readings=True,
                has_site_management=False,
                has_services=False,
                has_tariffs=False,
                has_roles=False,
                has_users=False,
                has_payment_details=False,
                has_payment_items=False,
            )
            self.stdout.write(
                self.style.SUCCESS("  Created role for staff (plumber)")
            )
            self.create_staff(
                "plumber@gmail.com", "admin123", plumber_role, "Plumber"
            )

    def create_owners(self):
        owners = [
            {
                "email": "ivan.ivanov@example.com",
                "first_name": "Jan",
                "last_name": "Kowalski",
                "date_of_birth": "1984-03-12",
                "external_id": 1001,
                "phone_number": "+79991112233",
                "viber": "+79991112233",
                "telegram": "@ivan_ivanov",
                "status": Status.ACTIVE,
                "notes": "Właściciel demonstracyjnego mieszkania.",
            },
            {
                "email": "anna.petrova@example.com",
                "first_name": "Anna",
                "last_name": "Nowak",
                "date_of_birth": "1990-09-28",
                "external_id": 1002,
                "phone_number": "+79992223344",
                "viber": "+79992223344",
                "telegram": "@anna_petrova",
                "status": Status.ACTIVE,
                "notes": "Preferuje kontakt przez e-mail.",
            },
            {
                "email": "petr.sidorov@example.com",
                "first_name": "Piotr",
                "last_name": "Wiśniewski",
                "date_of_birth": "1978-12-04",
                "external_id": 1003,
                "phone_number": "+79993334455",
                "viber": "+79993334455",
                "telegram": "@petr_sidorov",
                "status": Status.NEW,
                "notes": "Nowy właściciel, dokumenty w trakcie weryfikacji.",
            },
        ]

        for owner in owners:
            self.create_user(
                owner["email"],
                first_name=owner["first_name"],
                last_name=owner["last_name"],
                date_of_birth=owner["date_of_birth"],
                external_id=owner["external_id"],
                phone_number=owner["phone_number"],
                viber=owner["viber"],
                telegram=owner["telegram"],
                status=owner["status"],
                notes=owner["notes"],
                is_staff=False,
                is_superuser=False,
                is_active=owner["status"] == Status.ACTIVE,
                role=None,
            )

    def create_payment_details(self):
        payment_details, created = PaymentDetails.objects.update_or_create(
            company_name="Wspólnota Mieszkaniowa Centrum",
            defaults={
                "information": (
                    "Bank PKO: PL61 1090 1014 0000 0712 1981 2874\n"
                    "NIP: 525-000-00-00\n"
                    "W tytule przelewu podaj numer mieszkania."
                ),
            },
        )
        action = "Created" if created else "Updated"
        self.stdout.write(
            self.style.SUCCESS(
                f"  {action} payment details: {payment_details}"
            )
        )

    def create_payment_items(self):
        items = [
            ("Czynsz administracyjny", Type.INCOME),
            ("Zaliczka na media", Type.INCOME),
            ("Fundusz remontowy", Type.INCOME),
            ("Wynagrodzenia pracowników", Type.EXPENSE),
            ("Naprawy i konserwacja", Type.EXPENSE),
            ("Energia elektryczna części wspólnych", Type.EXPENSE),
        ]

        for name, item_type in items:
            item, created = PaymentItems.objects.update_or_create(
                name=name,
                defaults={"type": item_type},
            )
            action = "Created" if created else "Updated"
            self.stdout.write(
                self.style.SUCCESS(f"  {action} payment item: {item}")
            )

    def create_services(self):
        units = {
            "m²": "m²",
            "m³": "m³",
            "kWh": "kWh",
            "szt.": "szt.",
            "GJ": "GJ",
        }

        unit_objects = {}
        for title in units.values():
            unit, created = UnitsOfMeasurement.objects.get_or_create(
                title=title
            )
            unit_objects[title] = unit
            action = "Created" if created else "Exists"
            self.stdout.write(self.style.SUCCESS(f"  {action} unit: {unit}"))

        services = [
            ("Utrzymanie budynku", "m²", False),
            ("Zimna woda", "m³", True),
            ("Ciepła woda", "m³", True),
            ("Energia elektryczna", "kWh", True),
            ("Ogrzewanie", "GJ", True),
            ("Wywóz odpadów", "szt.", False),
        ]

        for title, unit_title, show in services:
            service, created = Services.objects.update_or_create(
                title=title,
                defaults={
                    "unit_of_measurement": unit_objects[unit_title],
                    "show": show,
                },
            )
            action = "Created" if created else "Updated"
            self.stdout.write(
                self.style.SUCCESS(f"  {action} service: {service}")
            )

    def create_tariffs(self):
        tariffs = [
            (
                "Podstawowy",
                "Standardowa taryfa dla lokali mieszkalnych.",
                {
                    "Utrzymanie budynku": 3.20,
                    "Zimna woda": 12.50,
                    "Ciepła woda": 28.00,
                    "Energia elektryczna": 1.10,
                    "Ogrzewanie": 65.00,
                    "Wywóz odpadów": 35.00,
                },
            ),
            (
                "Komfort",
                "Taryfa dla lokali z rozszerzonym pakietem usług.",
                {
                    "Utrzymanie budynku": 4.10,
                    "Zimna woda": 12.50,
                    "Ciepła woda": 28.00,
                    "Energia elektryczna": 1.10,
                    "Ogrzewanie": 65.00,
                    "Wywóz odpadów": 42.00,
                },
            ),
        ]

        for title, description, service_prices in tariffs:
            tariff, created = Tariffs.objects.update_or_create(
                title=title,
                defaults={"description": description},
            )
            action = "Created" if created else "Updated"
            self.stdout.write(
                self.style.SUCCESS(f"  {action} tariff: {tariff}")
            )

            for service_title, price in service_prices.items():
                service = Services.objects.get(title=service_title)
                service_tariff, created = (
                    ServiceTariffs.objects.update_or_create(
                        service=service,
                        tariff=tariff,
                        defaults={"price": price},
                    )
                )
                action = "Created" if created else "Updated"
                self.stdout.write(
                    self.style.SUCCESS(
                        f"  {action} service tariff: {service_tariff}"
                    )
                )

    def create_buildings(self):
        workers = list(
            Users.objects.filter(
                is_staff=True,
                is_active=True,
                status=Status.ACTIVE,
            )
        )
        owners = list(Users.objects.filter(is_staff=False).order_by("email"))
        tariff = Tariffs.objects.filter(title="Podstawowy").first()

        if not owners or tariff is None:
            self.stdout.write(
                self.style.WARNING(
                    "  Pominięto mieszkania: brak właścicieli lub taryfy."
                )
            )
            return

        buildings = [
            {
                "title": "Osiedle Słoneczne 1",
                "address": "ul. Słoneczna 1, Warszawa",
                "sections": ["Sekcja 1", "Sekcja 2"],
                "floors": ["Piętro 1", "Piętro 2", "Piętro 3"],
                "flats": [
                    (1, 48.50, "Sekcja 1", "Piętro 1", owners[0]),
                    (2, 62.30, "Sekcja 1", "Piętro 2", owners[1]),
                    (3, 55.00, "Sekcja 2", "Piętro 3", owners[2]),
                ],
            },
            {
                "title": "Dom Parkowy",
                "address": "ul. Słoneczna 2, Warszawa",
                "sections": ["Sekcja 1"],
                "floors": ["Piętro 1", "Piętro 2"],
                "flats": [
                    (1, 39.80, "Sekcja 1", "Piętro 1", owners[0]),
                    (2, 71.20, "Sekcja 1", "Piętro 2", owners[1]),
                ],
            },
        ]

        for building in buildings:
            house, created = Houses.objects.update_or_create(
                title=building["title"],
                defaults={"address": building["address"]},
            )
            house.workers.set(workers)
            action = "Created" if created else "Updated"
            self.stdout.write(self.style.SUCCESS(f"  {action} house: {house}"))

            sections = {}
            for title in building["sections"]:
                section, created = Sections.objects.update_or_create(
                    house=house,
                    title=title,
                    defaults={},
                )
                sections[title] = section
                action = "Created" if created else "Exists"
                self.stdout.write(
                    self.style.SUCCESS(f"  {action} section: {section}")
                )

            floors = {}
            for title in building["floors"]:
                floor, created = Floors.objects.update_or_create(
                    house=house,
                    title=title,
                    defaults={},
                )
                floors[title] = floor
                action = "Created" if created else "Exists"
                self.stdout.write(
                    self.style.SUCCESS(f"  {action} floor: {floor}")
                )

            for number, area, section_title, floor_title, owner in building[
                "flats"
            ]:
                flat, created = Flats.objects.update_or_create(
                    house=house,
                    number=number,
                    defaults={
                        "area": area,
                        "section": sections[section_title],
                        "floor": floors[floor_title],
                        "owner": owner,
                        "tariff": tariff,
                    },
                )
                action = "Created" if created else "Updated"
                self.stdout.write(
                    self.style.SUCCESS(f"  {action} flat: {flat}")
                )

    def create_pages(self):
        seo_main = SEO.objects.create(
            title="Strona główna",
            description="Strona główna firmy zarządzającej.",
            keywords="dom, mieszkanie, osiedle, usługi",
        )

        seo_about = SEO.objects.create(
            title="O nas",
            description="Informacje o naszej firmie.",
            keywords="o nas, firma, dyrektor",
        )

        seo_services = SEO.objects.create(
            title="Usługi",
            description="Lista świadczonych usług.",
            keywords="usługi, obsługa, administracja",
        )

        seo_contacts = SEO.objects.create(
            title="Kontakty",
            description="Dane kontaktowe firmy.",
            keywords="kontakty, telefon, adres",
        )

        MainPage.objects.create(
            slide1="main/slides/slide1.jpg",
            slide2="main/slides/slide2.jpg",
            slide3="main/slides/slide3.jpg",
            title="Witamy",
            description="Nowoczesne zarządzanie osiedlami mieszkaniowymi.",
            seo=seo_main,
            show_app_links=True,
        )

        AboutUsPage.objects.create(
            director_photo="about/director.jpg",
            title="O naszej firmie",
            description="Świadczymy profesjonalne usługi zarządzania nieruchomościami.",
            additional_title="Nasze doświadczenie",
            additional_description="Ponad 10 lat sukcesów.",
            seo=seo_about,
        )

        ServicePage.objects.create(
            seo=seo_services,
        )

        ContactPage.objects.create(
            title="Skontaktuj się z nami",
            description="Zawsze gotowi do pomocy.",
            ceo_name="Jan Kowalski",
            location="Warszawa",
            address="ul. Centralna 10",
            phone_number="+79991112233",
            email="info@example.com",
            web_page_url="https://example.com",
            map_url="""
            <style>
                .map-half-screen {
                    width: 100%;
                    height: 50vh; /* połowa wysokości ekranu */
                }

                .map-half-screen iframe {
                    width: 100%;
                    height: 100%;
                    border: 0;
                }
            </style>

            <div class="map-half-screen">
                <iframe
                    src="https://www.google.com/maps?q=50.4273684,30.525969&hl=ru&z=17&output=embed"
                    loading="lazy"
                    allowfullscreen
                    referrerpolicy="no-referrer-when-downgrade">
                </iframe>
            </div>
            """,
            seo=seo_contacts,
        )
