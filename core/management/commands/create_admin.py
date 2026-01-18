import os
from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model


class Command(BaseCommand):
    help = "Créer un superuser admin si absent (utilise variables d'env si présentes)"

    def handle(self, *args, **options):
        User = get_user_model()
        email = os.getenv("ADMIN_EMAIL", "admin@kiaba.local")
        username = os.getenv("ADMIN_USERNAME", "admin")
        password = os.getenv("ADMIN_PASSWORD", "admin1234")

        if User.objects.filter(username=username).exists():
            self.stdout.write(self.style.WARNING("Superuser déjà existant."))
            return

        User.objects.create_superuser(username=username, email=email, password=password)
        self.stdout.write(self.style.SUCCESS(f"Superuser créé: {username} / {email}"))
