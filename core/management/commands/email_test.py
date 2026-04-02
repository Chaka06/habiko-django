from django.core.management.base import BaseCommand
from django.core.mail import send_mail


class Command(BaseCommand):
    help = "Envoie un e-mail de test pour vérifier la configuration email"

    def add_arguments(self, parser):
        parser.add_argument("to_email", type=str)

    def handle(self, *args, **options):
        to_email = options["to_email"]
        send_mail(
            subject="[KIABA Rencontres] Test Email",
            message="Ceci est un e-mail de test.",
            from_email=None,
            recipient_list=[to_email],
            fail_silently=False,
        )
        self.stdout.write(self.style.SUCCESS(f"E-mail de test envoyé à {to_email}"))
