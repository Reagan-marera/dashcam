import os
import secrets
from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from api.models import Driver, Vehicle

class Command(BaseCommand):
    help = 'Seeds default database data securely (superuser, default driver, default vehicle)'

    def handle(self, *args, **options):
        # 1. Create superuser
        admin_username = os.getenv('SEED_ADMIN_USERNAME', 'admin')
        admin_email = os.getenv('SEED_ADMIN_EMAIL', 'admin@example.com')
        admin_pass = os.getenv('SEED_ADMIN_PASSWORD')

        is_random_admin_pass = False
        if not admin_pass:
            admin_pass = secrets.token_urlsafe(16)
            is_random_admin_pass = True

        if not User.objects.filter(username=admin_username).exists():
            User.objects.create_superuser(
                username=admin_username,
                email=admin_email,
                password=admin_pass
            )
            self.stdout.write(self.style.SUCCESS(f"Superuser '{admin_username}' created successfully."))
            if is_random_admin_pass:
                self.stdout.write(self.style.WARNING(f"Generated admin password: {admin_pass}"))
        else:
            self.stdout.write(self.style.WARNING(f"Superuser '{admin_username}' already exists."))

        # 2. Create driver
        driver_username = os.getenv('SEED_DRIVER_USERNAME', 'driver1')
        driver_user, created = User.objects.get_or_create(username=driver_username)
        if created:
            driver_pass = os.getenv('SEED_DRIVER_PASSWORD')
            is_random_driver_pass = False
            if not driver_pass:
                driver_pass = secrets.token_urlsafe(16)
                is_random_driver_pass = True
            driver_user.set_password(driver_pass)
            driver_user.save()
            self.stdout.write(self.style.SUCCESS(f"Driver user '{driver_username}' created successfully."))
            if is_random_driver_pass:
                self.stdout.write(self.style.WARNING(f"Generated driver password: {driver_pass}"))

        driver, created = Driver.objects.get_or_create(
            id=1,
            defaults={
                'user': driver_user,
                'name': 'John Doe',
                'license_number': 'DL-12345678',
                'phone': '+15551234567'
            }
        )
        if created:
            self.stdout.write(self.style.SUCCESS(f"Default driver '{driver.name}' created with ID=1."))
        else:
            self.stdout.write(self.style.WARNING(f"Default driver '{driver.name}' already exists."))

        # 3. Create vehicle
        vehicle, created = Vehicle.objects.get_or_create(
            id=1,
            defaults={
                'owner': driver,
                'registration': 'ABC-1234',
                'make': 'Toyota',
                'model': 'Camry',
                'year': 2022,
                'color': 'Silver',
                'vehicle_type': 'car'
            }
        )
        if created:
            self.stdout.write(self.style.SUCCESS(f"Default vehicle '{vehicle.registration}' created with ID=1."))
        else:
            self.stdout.write(self.style.WARNING(f"Default vehicle '{vehicle.registration}' already exists."))

        self.stdout.write(self.style.SUCCESS("Database seeding completed successfully!"))
