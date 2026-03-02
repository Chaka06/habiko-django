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


@shared_task
def expire_ads():
    """
    Supprime définitivement les annonces dont la date d'expiration est dépassée.
    Envoie l'email d'expiration puis supprime l'annonce et ses médias du storage.
    """
    import logging
    from accounts.email_service import EmailService
    from django.conf import settings

    logger = logging.getLogger(__name__)
    now = timezone.now()
    expired = Ad.objects.filter(expires_at__lte=now, status=Ad.Status.APPROVED).select_related("user", "city").prefetch_related("media")
    count = 0

    for ad in expired:
        try:
            # Email d'expiration
            EmailService.send_email(
                subject=f"Votre annonce '{ad.title}' a expiré et a été supprimée",
                to_emails=[ad.user.email],
                template_name="account/email/ad_expiration",
                context={
                    "user": ad.user,
                    "ad": ad,
                    "ad_url": f"{settings.SITE_URL}/ads/{ad.slug}/",
                },
                fail_silently=True,
            )
        except Exception as e:
            logger.warning("Email expiration annonce %s: %s", ad.id, e)

        # Supprimer les fichiers media du storage
        for media in ad.media.all():
            try:
                if media.image:
                    media.image.delete(save=False)
                if media.thumbnail:
                    media.thumbnail.delete(save=False)
            except Exception as e:
                logger.warning("Erreur suppression fichier media %s: %s", media.id, e)

        ad.delete()
        count += 1

    return f"{count} annonces supprimées"


@shared_task
def notify_expiring_soon_24h():
    """
    Envoie un email d'avertissement J-1 aux utilisateurs dont l'annonce expire
    dans les prochaines 23h–25h. Le flag expiry_notified_24h évite les doublons.
    """
    import logging
    from accounts.email_service import EmailService
    from django.conf import settings

    logger = logging.getLogger(__name__)
    now = timezone.now()
    window_start = now + timezone.timedelta(hours=23)
    window_end = now + timezone.timedelta(hours=25)

    ads = Ad.objects.filter(
        status=Ad.Status.APPROVED,
        expires_at__gte=window_start,
        expires_at__lte=window_end,
        expiry_notified_24h=False,
    ).select_related("user", "city")

    count = 0
    for ad in ads:
        try:
            EmailService.send_email(
                subject=f"Votre annonce expire demain – KIABA Rencontres",
                to_emails=[ad.user.email],
                template_name="account/email/ad_expiration_warning_24h",
                context={
                    "user": ad.user,
                    "ad": ad,
                    "ad_url": f"{settings.SITE_URL}/ads/{ad.slug}/",
                },
                fail_silently=True,
            )
            ad.expiry_notified_24h = True
            ad.save(update_fields=["expiry_notified_24h"])
            count += 1
        except Exception as e:
            logger.warning("Email J-1 annonce %s: %s", ad.id, e)

    return f"{count} emails J-1 envoyés"


@shared_task
def notify_expiring_soon_1h():
    """
    Envoie un email d'avertissement H-1 aux utilisateurs dont l'annonce expire
    dans les prochaines 45min–75min. Le flag expiry_notified_1h évite les doublons.
    """
    import logging
    from accounts.email_service import EmailService
    from django.conf import settings

    logger = logging.getLogger(__name__)
    now = timezone.now()
    window_start = now + timezone.timedelta(minutes=45)
    window_end = now + timezone.timedelta(minutes=75)

    ads = Ad.objects.filter(
        status=Ad.Status.APPROVED,
        expires_at__gte=window_start,
        expires_at__lte=window_end,
        expiry_notified_1h=False,
    ).select_related("user", "city")

    count = 0
    for ad in ads:
        try:
            EmailService.send_email(
                subject=f"Votre annonce expire dans 1 heure – KIABA Rencontres",
                to_emails=[ad.user.email],
                template_name="account/email/ad_expiration_warning_1h",
                context={
                    "user": ad.user,
                    "ad": ad,
                    "ad_url": f"{settings.SITE_URL}/ads/{ad.slug}/",
                },
                fail_silently=True,
            )
            ad.expiry_notified_1h = True
            ad.save(update_fields=["expiry_notified_1h"])
            count += 1
        except Exception as e:
            logger.warning("Email H-1 annonce %s: %s", ad.id, e)

    return f"{count} emails H-1 envoyés"


@shared_task
def promote_boosted_ads():
    """
    Remet en tête de liste (is_premium=True) toutes les annonces boostées actives.
    À planifier quotidiennement (ex. minuit heure CI = UTC).
    La remontée dure 2 heures (premium_until = now + 2h).
    """
    now = timezone.now()
    updated = Ad.objects.filter(
        is_boosted=True,
        boost_expires_at__gt=now,
        status=Ad.Status.APPROVED,
    ).update(
        is_premium=True,
        premium_until=now + timezone.timedelta(hours=2),
    )
    import logging
    logging.getLogger(__name__).info("promote_boosted_ads: %d annonces remontées", updated)
    return f"{updated} annonces boostées remontées en tête de liste"


@shared_task
def expire_premium_ads():
    """
    Remet is_premium=False pour les annonces dont le créneau premium est terminé.
    À planifier toutes les 15 minutes pour que la fenêtre 2h soit respectée.
    """
    now = timezone.now()
    updated = Ad.objects.filter(
        is_premium=True,
        premium_until__lt=now,
    ).update(is_premium=False)
    return f"{updated} annonces sorties du premium"


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
