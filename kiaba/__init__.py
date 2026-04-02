try:
    from .celery import app as celery_app
except Exception:  # Celery peut ne pas être installé/initialisé en environnement de vérification
    celery_app = None

__all__ = ("celery_app",)
