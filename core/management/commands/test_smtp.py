"""
Commande pour tester l'envoi d'email SMTP en production
"""
from django.core.management.base import BaseCommand
from django.conf import settings
from accounts.email_service import EmailService
import logging

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = "Test SMTP email sending"

    def add_arguments(self, parser):
        parser.add_argument(
            "--to",
            type=str,
            required=True,
            help="Email address to send test to",
        )

    def handle(self, *args, **options):
        to_email = options["to"]

        self.stdout.write("=" * 60)
        self.stdout.write("TEST D'ENVOI D'EMAIL")
        self.stdout.write("=" * 60)
        
        self.stdout.write(f"\n📧 Configuration actuelle:")
        self.stdout.write(f"  EMAIL_BACKEND: {settings.EMAIL_BACKEND}")
        self.stdout.write(f"  DEFAULT_FROM_EMAIL: {settings.DEFAULT_FROM_EMAIL}")
        self.stdout.write(f"  DEBUG: {settings.DEBUG}")
        
        self.stdout.write(f"\n📤 Tentative d'envoi d'email à: {to_email}")
        
        try:
            success = EmailService.send_email(
                subject="Test Email - KIABA Rencontres",
                to_emails=[to_email],
                text_content="""Bonjour,

Ceci est un email de test pour vérifier la configuration email de KIABA Rencontres.

Si vous recevez cet email, la configuration email fonctionne correctement.

Cordialement,
L'équipe KIABA Rencontres""",
                html_content="""<html>
<body style="font-family: Arial, sans-serif; padding: 20px;">
    <h2 style="color: #f97316;">Test Email - KIABA Rencontres</h2>
    <p>Bonjour,</p>
    <p>Ceci est un email de test pour vérifier la configuration email de KIABA Rencontres.</p>
    <p>Si vous recevez cet email, la configuration email fonctionne correctement.</p>
    <p>Cordialement,<br><strong>L'équipe KIABA Rencontres</strong></p>
</body>
</html>""",
                fail_silently=False,
            )
            
            if success:
                self.stdout.write(self.style.SUCCESS(f"\n✅ Email envoyé avec succès à {to_email}"))
                self.stdout.write("Vérifiez votre boîte mail (et les spams) pour confirmer la réception.")
            else:
                self.stdout.write(self.style.ERROR(f"\n❌ Échec de l'envoi d'email à {to_email}"))
                
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"\n❌ Erreur lors de l'envoi: {e}"))
            import traceback
            self.stdout.write(traceback.format_exc())

