"""
Service d'envoi d'emails professionnel pour HABIKO
Gère l'envoi d'emails avec templates HTML/text via SMTP
"""

import logging
from typing import List, Optional, Dict, Any
from django.utils.html import strip_tags

logger = logging.getLogger(__name__)


class EmailService:
    """Service centralisé pour l'envoi d'emails professionnels"""

    # Nom d'expéditeur standardisé
    FROM_NAME = "HABIKO"

    @classmethod
    def get_from_email_value(cls) -> str:
        """Retourne l'email depuis settings (lazy loading)"""
        try:
            from django.conf import settings

            return settings.DEFAULT_FROM_EMAIL
        except (ImportError, AttributeError):
            return "HABIKO <support@ci-habiko.com>"

    @classmethod
    def get_from_email(cls) -> str:
        """Retourne l'email formaté avec le nom HABIKO"""
        # Nettoyer l'email si il contient déjà le format
        email = cls.get_from_email_value()
        if "<" in email:
            # Extraire juste l'email
            import re

            match = re.search(r"<(.+?)>", email)
            if match:
                email = match.group(1)
        return f"{cls.FROM_NAME} <{email}>"

    @classmethod
    def send_email(
        cls,
        subject: str,
        to_emails: List[str],
        template_name: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None,
        text_content: Optional[str] = None,
        html_content: Optional[str] = None,
        fail_silently: bool = False,
    ) -> bool:
        """
        Envoie un email professionnel avec support HTML/text

        Args:
            subject: Sujet de l'email
            to_emails: Liste des destinataires
            template_name: Nom du template (sans extension, cherche .html et .txt)
            context: Contexte pour les templates
            text_content: Contenu texte brut (si pas de template)
            html_content: Contenu HTML brut (si pas de template)
            fail_silently: Si True, ne lève pas d'exception en cas d'erreur

        Returns:
            True si l'email a été envoyé avec succès, False sinon
        """
        if context is None:
            context = {}

        # Ajouter des valeurs par défaut au contexte
        try:
            from django.conf import settings

            site_url = getattr(settings, "SITE_URL", "https://ci-habiko.com")
            static_url = getattr(settings, "STATIC_URL", "/static/")
        except (ImportError, AttributeError):
            site_url = "https://ci-habiko.com"
            static_url = "/static/"

        context.setdefault("site_name", "HABIKO")
        context.setdefault("site_url", site_url)
        context.setdefault("support_email", "support@ci-habiko.com")
        context.setdefault("logo_url", f"{site_url}{static_url}img/logo.png")

        try:
            from django.template.loader import render_to_string
            from django.conf import settings

            # Générer le contenu depuis les templates si fourni
            if template_name:
                try:
                    html_content = render_to_string(f"{template_name}.html", context)
                    text_content = render_to_string(f"{template_name}.txt", context)
                except Exception as e:
                    logger.warning(
                        f"Template {template_name} non trouvé, utilisation du contenu brut: {e}"
                    )
                    if not text_content:
                        text_content = html_content and strip_tags(html_content) or ""

            # S'assurer qu'on a au moins du texte
            if not text_content and html_content:
                text_content = strip_tags(html_content)
            elif not text_content:
                text_content = subject

            # --- Envoi via SMTP (configuration dans settings.py) ---
            from django.core.mail import EmailMultiAlternatives

            email = EmailMultiAlternatives(
                subject=subject,
                body=text_content,
                from_email=cls.get_from_email(),
                to=to_emails,
            )
            if html_content:
                email.attach_alternative(html_content, "text/html")

            email_headers = getattr(settings, "EMAIL_HEADERS", {})
            for key, value in email_headers.items():
                email.extra_headers[key] = value
            email.extra_headers["Reply-To"] = "support@ci-habiko.com"
            email.extra_headers["Return-Path"] = "support@ci-habiko.com"

            try:
                logger.info(
                    f"📧 Envoi email via SMTP - Backend: {settings.EMAIL_BACKEND}, Host: {settings.EMAIL_HOST}, Port: {settings.EMAIL_PORT}"
                )
                logger.info(
                    f"📧 De: {cls.get_from_email()}, Vers: {', '.join(to_emails)}, Sujet: {subject}"
                )
                result = email.send(fail_silently=fail_silently)
                if result:
                    logger.info(
                        f"✅ Email envoyé avec succès via SMTP à {', '.join(to_emails)}: {subject}"
                    )
                else:
                    logger.warning(
                        f"⚠️ Email non envoyé (résultat: {result}) à {', '.join(to_emails)}"
                    )
                return bool(result)
            except Exception as send_error:
                logger.error(
                    f"❌ Erreur SMTP lors de l'envoi à {', '.join(to_emails)}: {send_error}",
                    exc_info=True,
                )
                if hasattr(send_error, "smtp_code"):
                    logger.error(
                        f"Code SMTP: {send_error.smtp_code}, Message: {send_error.smtp_error}"
                    )
                if hasattr(send_error, "args"):
                    logger.error(f"Détails erreur: {send_error.args}")
                logger.error(
                    f"Configuration SMTP: BACKEND={settings.EMAIL_BACKEND}, HOST={settings.EMAIL_HOST}, PORT={settings.EMAIL_PORT}, USER={settings.EMAIL_HOST_USER}, SSL={getattr(settings, 'EMAIL_USE_SSL', None)}, TLS={getattr(settings, 'EMAIL_USE_TLS', None)}"
                )
                if not fail_silently:
                    raise
                return False

        except Exception as e:
            logger.error(
                f"❌ Erreur lors de la préparation de l'email à {', '.join(to_emails)}: {e}",
                exc_info=True,
            )
            if not fail_silently:
                raise
            return False

    @classmethod
    def send_bulk_email(
        cls,
        subject: str,
        recipients: List[Dict[str, Any]],
        template_name: str,
        base_context: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, bool]:
        """
        Envoie des emails en masse avec contexte personnalisé par destinataire

        Args:
            subject: Sujet de l'email
            recipients: Liste de dicts avec 'email' et 'context'
            template_name: Nom du template
            base_context: Contexte de base partagé par tous

        Returns:
            Dict avec email -> True/False selon le succès
        """
        if base_context is None:
            base_context = {}

        results = {}

        for recipient in recipients:
            email = recipient["email"]
            context = {**base_context, **recipient.get("context", {})}

            try:
                success = cls.send_email(
                    subject=subject,
                    to_emails=[email],
                    template_name=template_name,
                    context=context,
                    fail_silently=True,
                )
                results[email] = success
            except Exception as e:
                logger.error(f"Erreur pour {email}: {e}")
                results[email] = False

        return results
