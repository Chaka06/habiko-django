"""
Service d'envoi d'emails professionnel pour HABIKO
Gère l'envoi d'emails avec templates HTML/text, retry automatique, et logging
"""
import logging
from typing import List, Optional, Dict, Any
from django.utils.html import strip_tags

logger = logging.getLogger(__name__)

BREVO_API_URL = "https://api.brevo.com/v3/smtp/email"


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
            match = re.search(r'<(.+?)>', email)
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
            site_url = getattr(settings, 'SITE_URL', 'https://ci-habiko.com')
            static_url = getattr(settings, 'STATIC_URL', '/static/')
        except (ImportError, AttributeError):
            site_url = 'https://ci-habiko.com'
            static_url = '/static/'
        
        context.setdefault('site_name', 'HABIKO')
        context.setdefault('site_url', site_url)
        context.setdefault('support_email', 'support@ci-habiko.com')
        context.setdefault('logo_url', f"{site_url}{static_url}img/logo.png")
        
        try:
            from django.template.loader import render_to_string
            from django.conf import settings
            import requests

            # Générer le contenu depuis les templates si fourni
            if template_name:
                try:
                    html_content = render_to_string(f"{template_name}.html", context)
                    text_content = render_to_string(f"{template_name}.txt", context)
                except Exception as e:
                    logger.warning(f"Template {template_name} non trouvé, utilisation du contenu brut: {e}")
                    if not text_content:
                        text_content = html_content and strip_tags(html_content) or ""
            
            # S'assurer qu'on a au moins du texte
            if not text_content and html_content:
                text_content = strip_tags(html_content)
            elif not text_content:
                text_content = subject

            # --- Envoi via API HTTP Brevo (recommandé sur Render) ---
            brevo_api_key = getattr(settings, "BREVO_API_KEY", None)
            # Log pour debug : vérifier si la clé est présente
            if brevo_api_key:
                # Afficher les premiers caractères pour vérifier le format (sécurité : ne pas logger la clé complète)
                key_preview = brevo_api_key[:20] + "..." if len(brevo_api_key) > 20 else brevo_api_key
                logger.info(f"🔑 BREVO_API_KEY trouvée (longueur: {len(brevo_api_key)}, début: {key_preview})")
            else:
                logger.warning(f"⚠️ BREVO_API_KEY non trouvée ou vide dans settings. Fallback vers SMTP.")
            if brevo_api_key and brevo_api_key.strip():
                try:
                    sender_email = cls.get_from_email_value()
                    # Extraire adresse email seule si besoin
                    if "<" in sender_email:
                        import re
                        m = re.search(r"<(.+?)>", sender_email)
                        if m:
                            sender_email = m.group(1)

                    logger.info(f"📧 Email sender: {sender_email}")

                    payload = {
                        "sender": {
                            "email": sender_email,
                            "name": cls.FROM_NAME,
                        },
                        "to": [{"email": e} for e in to_emails],
                        "subject": subject,
                        "htmlContent": html_content or text_content or subject,
                        "textContent": text_content or subject,
                    }
                    headers = {
                        "accept": "application/json",
                        "api-key": brevo_api_key,
                        "content-type": "application/json",
                    }

                    logger.info(
                        f"📧 Envoi via Brevo API à {', '.join(to_emails)} sujet='{subject}'"
                    )
                    resp = requests.post(BREVO_API_URL, json=payload, headers=headers, timeout=10)
                    if resp.status_code in (200, 201, 202):
                        logger.info(
                            f"✅ Email envoyé avec succès via Brevo API à {', '.join(to_emails)}"
                        )
                        return True
                    else:
                        error_msg = resp.text
                        logger.error(
                            f"❌ Erreur Brevo API ({resp.status_code}): {error_msg}"
                        )
                        # Si erreur 401 (clé invalide), donner un message plus clair
                        if resp.status_code == 401:
                            logger.error(
                                "⚠️ Erreur 401 Brevo API - Causes possibles :\n"
                                "1. La clé API (BREVO_API_KEY) est invalide ou a été révoquée\n"
                                "2. L'email sender ({}) n'est pas vérifié dans Brevo\n"
                                "3. La clé API n'a pas les permissions nécessaires\n"
                                "→ Vérifiez dans Brevo : Settings → SMTP & API → API Keys\n"
                                "→ Vérifiez aussi : Settings → Senders & IP → Senders (l'email doit être vérifié)"
                                .format(sender_email)
                            )
                        if not fail_silently:
                            resp.raise_for_status()
                        return False
                except Exception as api_error:
                    logger.error(
                        f"❌ Erreur lors de l'envoi via Brevo API à {', '.join(to_emails)}: {api_error}",
                        exc_info=True,
                    )
                    if not fail_silently:
                        raise
                    return False

            # --- Fallback SMTP classique (utile en local ou si SMTP dispo) ---
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
                    f"📧 Tentative d'envoi email SMTP - Backend: {settings.EMAIL_BACKEND}, Host: {settings.EMAIL_HOST}, Port: {settings.EMAIL_PORT}"
                )
                logger.info(
                    f"📧 Email de: {cls.get_from_email()}, Vers: {', '.join(to_emails)}, Sujet: {subject}"
                )
                result = email.send(fail_silently=fail_silently)
                logger.info(
                    f"✅ Email envoyé avec succès via SMTP à {', '.join(to_emails)}: {subject} (résultat: {result})"
                )
                return True
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
                    f"Configuration SMTP actuelle: BACKEND={settings.EMAIL_BACKEND}, HOST={settings.EMAIL_HOST}, PORT={settings.EMAIL_PORT}, SSL={getattr(settings, 'EMAIL_USE_SSL', None)}, TLS={getattr(settings, 'EMAIL_USE_TLS', None)}"
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
        connection = get_connection()
        
        try:
            connection.open()
            
            for recipient in recipients:
                email = recipient['email']
                context = {**base_context, **recipient.get('context', {})}
                
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
            
            connection.close()
            
        except Exception as e:
            logger.error(f"Erreur lors de l'envoi en masse: {e}", exc_info=True)
            connection.close()
        
        return results

