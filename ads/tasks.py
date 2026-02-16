from celery import shared_task
from django.utils import timezone
from django.db import transaction
from django.db.models import Q
from django.core.mail import send_mail
from .models import Ad, AdMedia
from accounts.tasks import send_ad_published_email


@shared_task(bind=True, max_retries=3)
def process_ad_media_image(self, media_id: int):
    """
    Traitement asynchrone : filigrane + miniature pour une image d'annonce.
    Une fois toutes les images de l'annonce traitées, l'annonce devient visible en liste (image_processing_done=True).
    """
    try:
        media = AdMedia.objects.select_related("ad").get(pk=media_id)
        if not media.image:
            return f"AdMedia {media_id}: pas d'image"
        if media._add_watermark_and_thumbnail():
            media.save(update_fields=["image", "thumbnail"])
        # L'annonce n'apparaît en liste que lorsque toutes les photos ont filigrane + miniature
        ad = media.ad
        pending = AdMedia.objects.filter(ad=ad).filter(Q(thumbnail="") | Q(thumbnail__isnull=True))
        if not pending.exists():
            ad.image_processing_done = True
            ad.save(update_fields=["image_processing_done"])
            from core.context_processors import invalidate_site_metrics_cache
            invalidate_site_metrics_cache()
        return f"AdMedia {media_id}: filigrane/thumbnail appliqués"
    except AdMedia.DoesNotExist:
        return f"AdMedia {media_id}: introuvable"
    except Exception as e:
        import logging
        logging.getLogger(__name__).warning("process_ad_media_image %s: %s", media_id, e)
        raise self.retry(exc=e, countdown=60)


@shared_task(bind=True, max_retries=3)
def expire_ads(self):
    """
    Supprime automatiquement les annonces expirées après 2 semaines.
    Supprime aussi les médias (images) associés pour éviter les fichiers orphelins.
    Envoie un email de notification à l'utilisateur.
    """
    from accounts.tasks import send_ad_expiration_email
    
    now = timezone.now()
    expired = Ad.objects.filter(expires_at__lte=now, status=Ad.Status.APPROVED)
    count = 0
    
    for ad in expired:
        # Envoyer l'email d'expiration AVANT de supprimer l'annonce
        try:
            send_ad_expiration_email.delay(ad.id)
        except Exception as e:
            # Logger mais ne pas bloquer la suppression
            import logging
            logger = logging.getLogger(__name__)
            logger.warning(f"Erreur envoi email expiration pour annonce {ad.id}: {e}")
        
        # Supprimer les médias (images) associés
        media_list = AdMedia.objects.filter(ad=ad)
        for media in media_list:
            if media.image:
                media.image.delete(save=False)  # Supprimer le fichier
            media.delete()  # Supprimer l'enregistrement
        
        # Supprimer l'annonce elle-même
        ad.delete()
        count += 1
    
    return f"{count} annonces expirées supprimées"


@shared_task(bind=True, max_retries=3)
def auto_approve_ad(self, ad_id: int):
    """Approuver automatiquement une annonce après 10 secondes"""
    try:
        ad = Ad.objects.get(pk=ad_id, status=Ad.Status.PENDING)
        ad.status = Ad.Status.APPROVED
        ad.save(update_fields=["status", "updated_at"])

        # Envoyer l'email de confirmation
        send_ad_published_email.delay(ad.id)

        print(f"Annonce {ad.id} approuvée automatiquement")
        return f"Annonce {ad.id} approuvée"
    except Ad.DoesNotExist:
        print(f"Annonce {ad_id} non trouvée ou déjà approuvée")
        return f"Annonce {ad_id} non trouvée"
    except Exception as e:
        print(f"Erreur lors de l'approbation automatique de l'annonce {ad_id}: {e}")
        return f"Erreur: {e}"


@shared_task(bind=True, max_retries=3)
def send_moderation_notification(self, ad_id: int, approved: bool, reason: str = ""):
    """
    Envoie un email de notification après modération d'une annonce.
    
    Args:
        ad_id: ID de l'annonce
        approved: True si approuvée, False si rejetée
        reason: Raison du rejet (optionnel)
    """
    try:
        from accounts.email_service import EmailService
        from django.conf import settings
        
        ad = Ad.objects.select_related('user', 'city').get(pk=ad_id)
        
        if not ad.user.email:
            return "Utilisateur sans email"
        
        # Choisir le template selon le statut
        template_name = "account/email/ad_approved" if approved else "account/email/ad_rejected"
        subject = f"Annonce {'approuvée' if approved else 'rejetée'} - {ad.title}"
        
        # Construire le contexte
        context = {
            "user": ad.user,
            "ad": ad,
            "ad_url": f"{settings.SITE_URL}/ads/{ad.slug}/",
            "reason": reason,
        }
        
        # Envoyer l'email avec le template HTML/texte
        EmailService.send_email(
            subject=subject,
            to_emails=[ad.user.email],
            template_name=template_name,
            context=context,
            fail_silently=False,
        )
        
        return f"Email de modération envoyé à {ad.user.email} (approuvé={approved})"
        
    except Ad.DoesNotExist:
        return f"Annonce {ad_id} introuvable"
    except Exception as e:
        # Retry automatique via Celery
        raise self.retry(exc=e, countdown=60)
