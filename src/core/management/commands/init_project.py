from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from django.core.files.base import ContentFile

from datetime import datetime, timedelta, date, time
import random
import os

from django.utils.text import slugify

from src.users.models import Roles
import config.settings as settings
Users = get_user_model()


class Command(BaseCommand):
    help = 'Initialize database with sample data for development/testing'

    def __init__(self):
        super().__init__()
        self.base_path = os.path.join(settings.BASE_DIR, 'gallery')


    def add_arguments(self, parser):
        parser.add_argument(
            '--clear',
            action='store_true',
            help='Clear existing data before initialization',
        )

    def get_image_file(self, image_path):
        full_path = os.path.join(self.base_path, image_path)
        self.stdout.write(self.style.WARNING(full_path))
        try:
            with open(full_path, 'rb') as f:
                return ContentFile(f.read(), name=os.path.basename(image_path))
        except FileNotFoundError:
            self.stdout.write(self.style.WARNING(f'Image not found: {full_path}'))

    def handle(self, *args, **options):
        if options['clear']:
            self.stdout.write(self.style.WARNING('Clearing existing data...'))
            self.clear_data()

        self.stdout.write(self.style.SUCCESS('Starting database initialization...'))

        # Create data in order of dependencies
        self.create_superuser()

        self.stdout.write(self.style.SUCCESS('Database initialization completed!'))

    def clear_data(self):
        models_to_clear = [Users]

        for model in models_to_clear:
            count = model.objects.count()
            model.objects.all().delete()
            self.stdout.write(f'  Deleted {count} {model.__name__} objects')

        Users.objects.filter(is_staff=False, is_superuser=False).delete()

    def create_superuser(self):
        if not Roles.objects.filter(role="Директор").exists():
            director_role = Roles.objects.create(
                role="Директор",
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
            )
            self.stdout.write(self.style.SUCCESS('  Created role for superuser (director)'))

            if not Users.objects.filter(email='admin@gmail.com').exists():
                Users.objects.create_superuser(
                    email='admin@gmail.com',
                    password='admin123',
                    first_name='Admin',
                    last_name='User',
                    phone_number='380951234567',
                    role=director_role,
                    is_staff=True,
                    is_superuser=True,
                )
                self.stdout.write(self.style.SUCCESS('  Created superuser (admin@gmail.com/admin123)'))
