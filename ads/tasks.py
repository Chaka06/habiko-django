from celery import shared_task
from django.utils import timezone
from django.core.mail import send_mail
from .models import Ad, AdMedia
from accounts.tasks import send_ad_published_email


@shared_task(bind=True, max_retries=3)
def expire_ads(self):
    """
    Supprime automatiquement les annonces expirées après 2 semaines.
    Supprime aussi les médias (images) associés pour éviter les fichiers orphelins.
    """
    now = timezone.now()
    expired = Ad.objects.filter(expires_at__lte=now, status=Ad.Status.APPROVED)
    count = 0
    for ad in expired:
        # Supprimer les médias (images) associés
        media_list = AdMedia.objects.filter(ad=ad)
        for media in media_list:
            if media.image:
                media.image.delete(save=False)  # Supprimer le fichier
            media.delete()  # Supprimer l'enregistrement
        
        # Supprimer l'annonce elle-même
        ad.delete()
        count += 1
        # Envoyer l'email d'expiration (désactivé temporairement pour éviter les erreurs Redis)
        # send_ad_expiration_email.delay(ad.id)
    return count


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
def send_moderation_notification(self, ad_id: int, approved: bool):
    try:
        ad = Ad.objects.get(pk=ad_id)
    except Ad.DoesNotExist:
        return 0
    if ad.user.email:
        subject = "[KIABA] Annonce approuvée" if approved else "[KIABA] Annonce rejetée"
        message = (
            f"Votre annonce '{ad.title}' a été approuvée."
            if approved
            else f"Votre annonce '{ad.title}' a été rejetée."
        )
        send_mail(subject=subject, message=message, from_email=None, recipient_list=[ad.user.email])
    return 1
