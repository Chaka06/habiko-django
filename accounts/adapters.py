from allauth.account.adapter import DefaultAccountAdapter
import logging

logger = logging.getLogger(__name__)

# Import lazy pour éviter les problèmes de chargement circulaire
try:
    from django.template.loader import render_to_string
    from django.conf import settings
except ImportError:
    # Si Django n'est pas encore chargé, on définira plus tard
    render_to_string = None
    settings = None


class NoRateLimitAccountAdapter(DefaultAccountAdapter):
    """Adaptateur personnalisé pour désactiver le rate limiting d'allauth et utiliser EmailService"""

    def is_ajax(self, request):
        """Désactiver la vérification AJAX pour éviter les erreurs"""
        return False

    def send_mail(self, template_prefix, email, context):
        """
        Surcharger l'envoi d'email pour utiliser EmailService avec templates HTML
        """
        # Import lazy pour éviter les problèmes de chargement
        try:
            from django.template.loader import render_to_string
            from .email_service import EmailService
        except (ImportError, AttributeError) as e:
            logger.error(f"❌ Erreur d'import dans send_mail: {e}", exc_info=True)
            # Fallback vers la méthode par défaut
            try:
                return super().send_mail(template_prefix, email, context)
            except Exception as fallback_error:
                logger.error(f"❌ Erreur même avec fallback: {fallback_error}", exc_info=True)
                return

        # Enrichir le contexte avec les valeurs par défaut (logo, site_name, etc.)
        try:
            from django.conf import settings

            site_url = getattr(settings, "SITE_URL", "https://ci-kiaba.com")
            static_url = getattr(settings, "STATIC_URL", "/static/")

            # Ajouter les valeurs par défaut au contexte si elles n'existent pas
            context.setdefault("site_name", "KIABA Rencontres")
            context.setdefault("site_url", site_url)
            context.setdefault("support_email", "support@ci-kiaba.com")
            # Logo du site en URL absolue (?v=3 = même que le site, évite cache ancien)
            base = site_url.rstrip("/")
            context.setdefault("logo_url", f"{base}/static/img/logo.png?v=3")

            # Pour les emails de confirmation, construire activate_url si key est présent
            # Allauth peut passer 'key' ou 'activate_url' dans le contexte
            if "key" in context and "activate_url" not in context:
                try:
                    from django.urls import reverse

                    key = context["key"]
                    # Construire l'URL complète avec le bon domaine
                    activate_url = f"{site_url}{reverse('account_confirm_email', args=[key])}"
                    context["activate_url"] = activate_url
                    logger.info(f"📧 activate_url construit depuis key: {activate_url}")
                except Exception as e:
                    logger.warning(f"Impossible de construire activate_url depuis key: {e}")
            elif "activate_url" in context:
                # Si activate_url existe mais est relatif, le rendre absolu
                # Ou si c'est une URL absolue avec un mauvais domaine, la remplacer
                activate_url = context["activate_url"]
                if activate_url:
                    if not activate_url.startswith("http"):
                        # URL relative, la rendre absolue
                        context["activate_url"] = f"{site_url}{activate_url}"
                        logger.info(f"📧 activate_url rendu absolu: {context['activate_url']}")
                    elif (
                        "localhost" in activate_url
                        or "example.com" in activate_url
                        or "127.0.0.1" in activate_url
                    ):
                        # URL absolue avec mauvais domaine, extraire le chemin et reconstruire
                        from urllib.parse import urlparse

                        parsed = urlparse(activate_url)
                        path = parsed.path
                        context["activate_url"] = f"{site_url}{path}"
                        logger.info(
                            f"📧 activate_url corrigé (mauvais domaine): {context['activate_url']}"
                        )
        except Exception as e:
            logger.warning(f"Erreur lors de l'enrichissement du contexte: {e}")

        # Logger le template_prefix pour debug
        try:
            logger.info(
                f"📧 send_mail appelé avec template_prefix: {template_prefix}, email: {email}"
            )
        except Exception:
            pass  # Ne pas bloquer si le logging échoue

        # Déterminer le template à utiliser selon le type d'email
        template_map = {
            "account/email/email_confirmation": {
                "html_template": "account/email/email_confirmation.html",
                "text_template": "account/email/email_confirmation_message.txt",
                "subject_template": "account/email/email_confirmation_subject.txt",
            },
            "account/email/password_reset": {
                "html_template": "account/email/password_reset.html",
                "text_template": "account/email/password_reset_message.txt",
                "subject_template": "account/email/password_reset_subject.txt",
            },
        }

        # Chercher le template correspondant (plusieurs formats possibles)
        template_info = None
        for key, info in template_map.items():
            # Vérifier plusieurs formats de template_prefix
            if (
                template_prefix.startswith(key)
                or key in template_prefix
                or template_prefix.endswith(key.split("/")[-1])
                or key.split("/")[-1] in template_prefix
            ):
                template_info = info
                logger.info(f"✅ Template trouvé pour {template_prefix}: {key}")
                break

        try:
            # Si on a un template HTML personnalisé, l'utiliser
            if template_info:
                # Rendre le sujet
                try:
                    subject = render_to_string(template_info["subject_template"], context).strip()
                    # Nettoyer le sujet (enlever les sauts de ligne)
                    subject = " ".join(subject.split())
                except Exception as e:
                    logger.warning(f"Erreur lors du rendu du sujet pour {template_prefix}: {e}")
                    subject = context.get("subject", "Message de KIABA Rencontres")

                # Rendre le contenu HTML et texte
                try:
                    html_content = render_to_string(template_info["html_template"], context)
                except Exception as e:
                    logger.warning(f"Erreur lors du rendu HTML pour {template_prefix}: {e}")
                    html_content = None

                try:
                    text_content = render_to_string(template_info["text_template"], context)
                except Exception as e:
                    logger.warning(f"Erreur lors du rendu texte pour {template_prefix}: {e}")
                    text_content = None

                # Envoyer via EmailService
                # SUR VERCEL : envoi synchrone obligatoire (la fonction serverless s'arrête dès la réponse,
                # un thread en arrière-plan n'a pas le temps d'envoyer l'email)
                import os

                def _do_send():
                    try:
                        EmailService.send_email(
                            subject=subject,
                            to_emails=[email],
                            html_content=html_content,
                            text_content=text_content,
                            context=context,
                            fail_silently=True,
                        )
                    except Exception as e:
                        logger.error(f"❌ Envoi email {template_prefix} échoué: {e}")

                try:
                    if os.environ.get("VERCEL") == "1":
                        _do_send()  # Synchrone sur Vercel
                    else:
                        import threading
                        thread = threading.Thread(target=_do_send, daemon=True)
                        thread.start()
                    logger.info(f"📧 Email {template_prefix} envoyé à {email}")
                    return
                except Exception as email_error:
                    logger.error(
                        f"❌ Erreur lors de l'envoi de l'email {template_prefix} à {email}: {email_error}"
                    )
                    return  # Ne jamais bloquer le flux d'inscription
            else:
                # Pour les autres types d'emails, utiliser la méthode par défaut mais avec EmailService
                # Rendre le sujet
                try:
                    subject = render_to_string(f"{template_prefix}_subject.txt", context).strip()
                except Exception:
                    subject = context.get("subject", "Message de KIABA Rencontres")

                # Rendre le contenu texte
                try:
                    text_content = render_to_string(f"{template_prefix}_message.txt", context)
                except Exception:
                    text_content = context.get("message", "")

                # Essayer de trouver un template HTML correspondant
                html_content = None
                try:
                    # Chercher un template HTML avec le même nom
                    html_template = (
                        template_prefix.replace("_message", "").replace("_subject", "") + ".html"
                    )
                    html_content = render_to_string(html_template, context)
                except Exception:
                    pass

                # Envoyer via EmailService (même logique : synchrone sur Vercel)
                import os

                def _do_send():
                    try:
                        EmailService.send_email(
                            subject=subject,
                            to_emails=[email],
                            html_content=html_content,
                            text_content=text_content,
                            context=context,
                            fail_silently=True,
                        )
                    except Exception as e:
                        logger.error(f"❌ Envoi email {template_prefix} échoué: {e}")

                try:
                    if os.environ.get("VERCEL") == "1":
                        _do_send()
                    else:
                        import threading
                        thread = threading.Thread(target=_do_send, daemon=True)
                        thread.start()
                    logger.info(f"📧 Email {template_prefix} envoyé à {email}")
                    return
                except Exception as email_error:
                    logger.error(
                        f"❌ Erreur lors de l'envoi de l'email {template_prefix} à {email}: {email_error}"
                    )
                    return  # Ne jamais bloquer le flux

        except Exception as e:
            logger.error(
                f"❌ Erreur lors de l'envoi d'email {template_prefix} via EmailService: {e}",
                exc_info=True,
            )
            # Ne pas utiliser le fallback d'allauth car il utilisera aussi SMTP et échouera de la même manière
            # L'utilisateur pourra renvoyer l'email de confirmation plus tard depuis l'interface
            logger.warning(
                f"⚠️ Impossible d'envoyer l'email {template_prefix} à {email}. L'utilisateur pourra le renvoyer plus tard."
            )
            return

    def add_message(self, request, level, message_template=None, message_context=None, extra_tags="", message=None):
        """
        Ne pas ajouter de messages allauth (connexion réussie, déconnexion, etc.)
        pour éviter d'afficher des toasts / bannières non stylées.
        """
        return  # pas de message

    def get_login_redirect_url(self, request):
        """Redirection après connexion"""
        # Vérifier que l'utilisateur est authentifié
        if not request.user or not request.user.is_authenticated:
            return "/auth/login/"

        # Marquer le profil comme vérifié après la première connexion
        try:
            from .models import Profile

            try:
                profile = request.user.profile
                if not profile.is_verified:
                    profile.is_verified = True
                    profile.save()
                    logger.info(f"Profil de {request.user.username} marqué comme vérifié")
            except Profile.DoesNotExist:
                # Créer le profil s'il n'existe pas
                profile = Profile.objects.create(
                    user=request.user, display_name=request.user.username
                )
                logger.info(f"Profil créé pour {request.user.username}")
        except Exception as e:
            logger.error(f"Erreur lors de la gestion du profil: {e}", exc_info=True)

        # Envoyer l'email de notification de connexion (en arrière-plan, ne pas bloquer)
        try:
            from .tasks import send_login_notification_email

            # En mode Render sans Redis, les tâches sont exécutées en mode synchrone.
            # Appeler directement la fonction pour éviter les comportements étranges de Celery.
            send_login_notification_email(request.user.id)
        except Exception as e:
            logger.error(f"Erreur lors de l'envoi de l'email de notification: {e}", exc_info=True)

        return "/dashboard/"

    def get_logout_redirect_url(self, request):
        """Redirection après déconnexion"""
        return "/"

    def is_auto_signup_allowed(self, request, sociallogin):
        """Autoriser l'inscription automatique"""
        return True

    def is_open_for_signup(self, request):
        """Site ouvert aux inscriptions"""
        return True
