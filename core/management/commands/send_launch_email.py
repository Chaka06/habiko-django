"""
Commande pour envoyer l'email de lancement payant à tous les utilisateurs
extraits du fichier account_emailaddress_rows.sql.

Usage :
  # Tester sans envoyer (affiche les adresses)
  python manage.py send_launch_email --dry-run

  # Envoyer seulement aux 3 premiers (test réel)
  python manage.py send_launch_email --limit 3

  # Envoyer à tous
  python manage.py send_launch_email
"""

import re
import os
import time
import logging

from django.core.management.base import BaseCommand
from django.conf import settings

logger = logging.getLogger(__name__)

SQL_FILE = os.path.join(settings.BASE_DIR, "account_emailaddress_rows.sql")


def _parse_emails(sql_file: str) -> list[str]:
    """Extrait toutes les adresses email depuis le fichier SQL INSERT."""
    with open(sql_file, "r", encoding="utf-8") as f:
        content = f.read()
    # Chaque ligne VALUES (..., 'email@domain.com', verified, primary, user_id), ...
    emails = re.findall(r"\(\d+,\s*'([^']+@[^']+)'", content)
    # Dédoublonner et nettoyer
    seen = set()
    result = []
    for email in emails:
        email = email.strip().lower()
        if email and email not in seen:
            seen.add(email)
            result.append(email)
    return result


class Command(BaseCommand):
    help = "Envoie l'email de lancement payant à tous les utilisateurs du fichier SQL"

    def add_arguments(self, parser):
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Affiche les adresses sans envoyer d'email",
        )
        parser.add_argument(
            "--limit",
            type=int,
            default=0,
            help="Limite le nombre d'emails envoyés (0 = tous)",
        )
        parser.add_argument(
            "--delay",
            type=float,
            default=0.3,
            help="Délai en secondes entre chaque envoi (défaut: 0.3s)",
        )

    def handle(self, *args, **options):
        from accounts.email_service import EmailService

        dry_run = options["dry_run"]
        limit = options["limit"]
        delay = options["delay"]

        if not os.path.exists(SQL_FILE):
            self.stderr.write(self.style.ERROR(f"Fichier SQL introuvable : {SQL_FILE}"))
            return

        emails = _parse_emails(SQL_FILE)
        total = len(emails)
        self.stdout.write(f"Emails trouvés dans le fichier SQL : {total}")

        if limit > 0:
            emails = emails[:limit]
            self.stdout.write(f"Limite appliquée : {len(emails)} emails")

        if dry_run:
            self.stdout.write(self.style.WARNING("=== DRY RUN — aucun email envoyé ==="))
            for i, email in enumerate(emails, 1):
                self.stdout.write(f"  {i:>3}. {email}")
            return

        self.stdout.write(f"Envoi en cours vers {len(emails)} destinataires...")

        sent = 0
        failed = 0

        for i, email in enumerate(emails, 1):
            try:
                success = EmailService.send_email(
                    subject="KIABA Rencontres évolue — Nouvelles fonctionnalités et forfaits",
                    to_emails=[email],
                    template_name="account/email/newsletter_launch",
                    context={},
                    fail_silently=True,
                )
                if success:
                    sent += 1
                    self.stdout.write(f"  [{i}/{len(emails)}] OK   {email}")
                else:
                    failed += 1
                    self.stdout.write(
                        self.style.WARNING(f"  [{i}/{len(emails)}] FAIL {email}")
                    )
            except Exception as e:
                failed += 1
                self.stdout.write(
                    self.style.ERROR(f"  [{i}/{len(emails)}] ERR  {email} — {e}")
                )

            if delay > 0 and i < len(emails):
                time.sleep(delay)

        self.stdout.write("")
        self.stdout.write(
            self.style.SUCCESS(f"Terminé : {sent} envoyés, {failed} échecs sur {len(emails)}")
        )
