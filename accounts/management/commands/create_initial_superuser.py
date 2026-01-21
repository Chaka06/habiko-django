from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model


class Command(BaseCommand):
    help = (
        "Crée automatiquement un superutilisateur pour HABIKO si il n'existe pas "
        "(utilisateur: kaliadmin2)."
    )

    def handle(self, *args, **options):
        User = get_user_model()
        from django.conf import settings

        username = "kaliadmin2"
        # Utiliser une variable d'environnement pour le mot de passe (plus sécurisé)
        password = getattr(settings, "INITIAL_SUPERUSER_PASSWORD", "Ch@coul@melo72")
        email = "admin@ci-habiko.com"

        if User.objects.filter(username=username).exists():
            self.stdout.write(
                self.style.WARNING(
                    f"Le superutilisateur '{username}' existe déjà, aucune action effectuée."
                )
            )
            return

        user = User.objects.create_superuser(
            username=username,
            email=email,
            password=password,
        )

        self.stdout.write(
            self.style.SUCCESS(
                f"Superutilisateur créé avec succès : {username} / {password}"
            )
        )

