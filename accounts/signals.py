from django.dispatch import receiver
from django.contrib.auth.signals import user_logged_in
from django.db.models.signals import pre_save, post_save
from django.conf import settings

from .models import CustomUser
from .tasks import (
    send_login_notification_email,
    send_password_change_email,
    send_account_created_email,
)


@receiver(user_logged_in)
def on_user_logged_in(sender, user, request, **kwargs):  # pragma: no cover
    try:
        # S'assurer que le profil existe
        from .models import Profile
        if not hasattr(user, 'profile'):
            try:
                Profile.objects.get(user=user)
            except Profile.DoesNotExist:
                Profile.objects.create(
                    user=user,
                    display_name=user.username
                )
    except Exception as e:
        import logging
        logger = logging.getLogger(__name__)
        logger.error(f"Erreur lors de la création du profil: {e}", exc_info=True)
    
    try:
        # Envoyer l'email immédiatement en production
        from django.conf import settings

        if not settings.DEBUG:
            send_login_notification_email.delay(user.id)
    except Exception as e:
        import logging
        logger = logging.getLogger(__name__)
        logger.error(f"Erreur lors de l'envoi de l'email de notification: {e}", exc_info=True)
        # Let login proceed; task retries will handle transient errors


@receiver(pre_save, sender=CustomUser)
def remember_old_password(sender, instance: CustomUser, **kwargs):  # pragma: no cover
    if not instance.pk:
        instance._old_password = None
        return
    try:
        old = CustomUser.objects.get(pk=instance.pk)
        instance._old_password = old.password
    except CustomUser.DoesNotExist:
        instance._old_password = None


@receiver(post_save, sender=CustomUser)
def on_user_saved(sender, instance: CustomUser, created: bool, **kwargs):  # pragma: no cover
    if created:
        # Send account created email
        try:
            from django.conf import settings

            if not settings.DEBUG:
                send_account_created_email.delay(instance.id)
        except Exception:
            pass
        return

    # Password change detection
    old_password = getattr(instance, "_old_password", None)
    if old_password and old_password != instance.password:
        try:
            from django.conf import settings

            if not settings.DEBUG:
                send_password_change_email.delay(instance.id)
        except Exception:
            pass
