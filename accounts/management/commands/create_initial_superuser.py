import os
from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from django.conf import settings


class Command(BaseCommand):
    help = (
        "Crée automatiquement un superutilisateur pour KIABA Rencontres si il n'existe pas. "
        "Utilisateur: admin2. Mot de passe: variable d'environnement INITIAL_SUPERUSER_PASSWORD."
    )

    def handle(self, *args, **options):
        User = get_user_model()

        username = "admin2"
        password = getattr(settings, "INITIAL_SUPERUSER_PASSWORD", None) or os.environ.get(
            "INITIAL_SUPERUSER_PASSWORD", ""
        ).strip()
        email = "admin@ci-kiaba.com"

        if not password:
            self.stdout.write(
                self.style.ERROR(
                    "Définissez INITIAL_SUPERUSER_PASSWORD (variable d'environnement ou settings) pour créer le superuser."
                )
            )
            return

        if User.objects.filter(username=username).exists():
            self.stdout.write(
                self.style.WARNING(
                    f"Le superutilisateur '{username}' existe déjà, aucune action effectuée."
                )
            )
            return

        User.objects.create_superuser(
            username=username,
            email=email,
            password=password,
        )

        self.stdout.write(self.style.SUCCESS(f"Superutilisateur créé : {username}"))
