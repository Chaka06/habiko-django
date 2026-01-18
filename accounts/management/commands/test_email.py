from django.core.management.base import BaseCommand
from accounts.tasks import send_profile_validation_email, send_account_created_email
from accounts.models import Profile, CustomUser


class Command(BaseCommand):
    help = "Tester l'envoi d'emails de validation"

    def add_arguments(self, parser):
        parser.add_argument(
            "--profile-id",
            type=int,
            help="ID du profil à valider",
        )
        parser.add_argument(
            "--user-id",
            type=int,
            help="ID de l'utilisateur pour l'email de création",
        )

    def handle(self, *args, **options):
        if options["profile_id"]:
            profile_id = options["profile_id"]
            try:
                Profile.objects.get(id=profile_id)
                result = send_profile_validation_email(profile_id)
                self.stdout.write(self.style.SUCCESS(f"Email de validation envoyé : {result}"))
            except Profile.DoesNotExist:
                self.stdout.write(self.style.ERROR(f"Profil {profile_id} introuvable"))

        if options["user_id"]:
            user_id = options["user_id"]
            try:
                CustomUser.objects.get(id=user_id)
                result = send_account_created_email(user_id)
                self.stdout.write(self.style.SUCCESS(f"Email de création envoyé : {result}"))
            except CustomUser.DoesNotExist:
                self.stdout.write(self.style.ERROR(f"Utilisateur {user_id} introuvable"))

        if not options["profile_id"] and not options["user_id"]:
            self.stdout.write(
                self.style.WARNING(
                    "Utilisez --profile-id ou --user-id pour spécifier quel email envoyer"
                )
            )
