from celery import shared_task
from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.conf import settings
from .models import Profile
from .email_service import EmailService
import logging

logger = logging.getLogger(__name__)


@shared_task(
    bind=True,
    autoretry_for=(Exception,),
    retry_kwargs={"max_retries": 5, "countdown": 60},
    retry_backoff=True,
    retry_backoff_max=600,
    retry_jitter=True,
)
def send_profile_validation_email(self, profile_id):
    """Envoyer un email de validation de profil"""
    try:
        profile = Profile.objects.get(id=profile_id)
        user = profile.user

        # Créer le lien de validation (à implémenter selon tes besoins)
        validation_url = f"{settings.SITE_URL}/accounts/validate-profile/{profile.id}/"

        subject = "Validation de votre profil HABIKO"

        message = f"""
Bonjour {user.username},

Votre profil a été créé avec succès sur HABIKO !

Pour finaliser votre inscription et commencer à publier des annonces, veuillez cliquer sur le lien ci-dessous pour valider votre profil :

{validation_url}

Informations de votre profil :
- Nom d'affichage : {profile.display_name}
- Ville : {profile.city}
- Méthodes de contact : {', '.join(profile.contact_prefs) if profile.contact_prefs else 'Non définies'}

Une fois validé, vous pourrez :
- Publier des annonces gratuitement
- Gérer vos préférences de contact
- Suivre les statistiques de vos annonces

Si vous n'avez pas créé de compte sur HABIKO, veuillez ignorer cet email.

Cordialement,
L'équipe HABIKO
{settings.DEFAULT_FROM_EMAIL}
        """

        # Utiliser le nouveau service d'email
        EmailService.send_email(
            subject=subject,
            to_emails=[user.email],
            text_content=message,
            fail_silently=False,
        )

        return f"Email de validation envoyé à {user.email}"

    except Profile.DoesNotExist:
        return f"Profil {profile_id} introuvable"
    except Exception as e:
        raise e


@shared_task(
    bind=True,
    autoretry_for=(Exception,),
    retry_kwargs={"max_retries": 5, "countdown": 60},
    retry_backoff=True,
    retry_backoff_max=600,
    retry_jitter=True,
)
def send_account_created_email(self, user_id):
    """Envoyer un email de confirmation de création de compte avec lien de confirmation"""
    try:
        from .models import CustomUser
        from allauth.account.models import EmailConfirmation, EmailAddress
        from django.urls import reverse
        from django.conf import settings

        user = CustomUser.objects.get(id=user_id)

        # Obtenir le lien de confirmation d'email
        confirmation_url = None
        try:
            # Récupérer l'adresse email non confirmée
            email_address = EmailAddress.objects.filter(user=user, verified=False).first()
            if email_address:
                # Créer ou récupérer la confirmation
                confirmation = EmailConfirmation.create(email_address)
                confirmation_url = confirmation.get_confirm_url()
                # Construire l'URL complète
                if not confirmation_url.startswith('http'):
                    confirmation_url = f"{settings.SITE_URL}{confirmation_url}"
        except Exception as e:
            logger.warning(f"Impossible de créer le lien de confirmation: {e}")

        subject = "Compte créé avec succès sur HABIKO"

        # Message texte
        message = f"""Bonjour {user.username},

Bienvenue sur HABIKO, la plateforme immobilière N°1 en Côte d'Ivoire !

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
ACTIVATION DE VOTRE COMPTE
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Pour activer votre compte et commencer à publier vos annonces, veuillez cliquer sur le lien ci-dessous :

{confirmation_url if confirmation_url else "Un email de confirmation vous sera envoyé séparément."}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Une fois votre compte activé, vous pourrez :
✓ Publier des annonces gratuitement
✓ Gérer votre profil et vos préférences de contact
✓ Suivre les statistiques de vos annonces
✓ Recevoir des notifications importantes

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

⚠️ Si vous n'avez pas créé de compte sur HABIKO, veuillez ignorer cet email.

Cordialement,
L'équipe HABIKO
{settings.SITE_URL}
        """

        # Utiliser le nouveau service d'email avec template HTML
        EmailService.send_email(
            subject=subject,
            to_emails=[user.email],
            template_name="account/email/account_created",
            context={
                "user": user,
                "confirmation_url": confirmation_url,
                "site_url": settings.SITE_URL,
            },
            text_content=message if not confirmation_url else None,  # Utiliser le template si on a l'URL
            fail_silently=True,  # Ne pas bloquer l'inscription si l'email échoue
        )

        return f"Email de confirmation envoyé à {user.email}"

    except Exception as e:
        logger.exception(f"Erreur lors de l'envoi de l'email de création de compte: {e}")
        raise e


@shared_task(
    bind=True,
    autoretry_for=(Exception,),
    retry_kwargs={"max_retries": 5, "countdown": 60},
    retry_backoff=True,
    retry_backoff_max=600,
    retry_jitter=True,
)
def send_ad_published_email(self, ad_id):
    """Email de confirmation quand une annonce est publiée"""
    try:
        from ads.models import Ad

        ad = Ad.objects.get(id=ad_id)
        user = ad.user

        context = {
            "user": user,
            "ad": ad,
            "site_name": "HABIKO",
            "site_url": settings.SITE_URL,
            "ad_url": f"{settings.SITE_URL}/ads/{ad.slug}/",
        }

        subject = f"Votre annonce '{ad.title}' est en ligne !"
        
        # Utiliser le nouveau service d'email avec support HTML
        EmailService.send_email(
            subject=subject,
            to_emails=[user.email],
            template_name="account/email/ad_published",
            context=context,
            fail_silently=False,
        )
        
        return f"Email de publication envoyé à {user.email}"
    except Exception as e:
        raise e


@shared_task
def send_login_notification_email(user_id):
    """Email de notification à chaque connexion"""
    try:
        from django.contrib.auth import get_user_model

        User = get_user_model()
        user = User.objects.get(id=user_id)

        context = {
            "user": user,
            "site_name": "HABIKO",
            "site_url": settings.SITE_URL,
        }

        subject = "Connexion détectée sur votre compte"
        
        # Utiliser le nouveau service d'email
        # Ne jamais bloquer la connexion à cause d'un email
        EmailService.send_email(
            subject=subject,
            to_emails=[user.email],
            template_name="account/email/login_notification",
            context=context,
            fail_silently=True,
        )
        
        return f"Email de notification de connexion envoyé à {user.email}"
    except Exception as e:
        # Loguer mais ne jamais faire échouer la requête
        logger.exception(f"Erreur lors de l'envoi de l'email de notification de connexion: {e}")
        return f"Echec d'envoi de l'email de notification pour {user_id}"


@shared_task(
    bind=True,
    autoretry_for=(Exception,),
    retry_kwargs={"max_retries": 5, "countdown": 60},
    retry_backoff=True,
    retry_backoff_max=600,
    retry_jitter=True,
)
def send_password_change_email(self, user_id):
    """Email de confirmation lors du changement de mot de passe"""
    try:
        from django.contrib.auth import get_user_model

        User = get_user_model()
        user = User.objects.get(id=user_id)

        context = {
            "user": user,
            "site_name": "HABIKO",
            "site_url": settings.SITE_URL,
        }

        subject = "Mot de passe modifié avec succès"
        
        # Utiliser le nouveau service d'email avec support HTML
        EmailService.send_email(
            subject=subject,
            to_emails=[user.email],
            template_name="account/email/password_change",
            context=context,
            fail_silently=False,
        )
        
        return f"Email de changement de mot de passe envoyé à {user.email}"
    except Exception as e:
        raise e


@shared_task(
    bind=True,
    autoretry_for=(Exception,),
    retry_kwargs={"max_retries": 5, "countdown": 60},
    retry_backoff=True,
    retry_backoff_max=600,
    retry_jitter=True,
)
def send_ad_expiration_email(self, ad_id):
    """Email de notification quand une annonce expire"""
    try:
        from ads.models import Ad

        ad = Ad.objects.get(id=ad_id)
        user = ad.user

        context = {
            "user": user,
            "ad": ad,
            "site_name": "HABIKO",
            "site_url": settings.SITE_URL,
            "ad_url": f"{settings.SITE_URL}/ads/{ad.slug}/",
        }

        subject = f"Votre annonce '{ad.title}' a expiré"
        
        # Utiliser le nouveau service d'email
        EmailService.send_email(
            subject=subject,
            to_emails=[user.email],
            template_name="account/email/ad_expiration",
            context=context,
            fail_silently=False,
        )
        
        return f"Email d'expiration envoyé à {user.email}"
    except Exception as e:
        raise e
