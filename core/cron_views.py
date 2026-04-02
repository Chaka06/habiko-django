"""
Endpoints HTTP pour les cron jobs (Vercel Cron + cron-job.org).
Chaque endpoint exécute une tâche planifiée directement (sans Celery worker).
Protégé par CRON_SECRET dans le header Authorization ou en query param.
"""
import logging
from django.conf import settings
from django.http import HttpRequest, JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_GET

logger = logging.getLogger(__name__)

CRON_SECRET = getattr(settings, "CRON_SECRET", "")


def _check_auth(request: HttpRequest) -> bool:
    """Vérifie le secret dans Authorization header ou ?secret= query param."""
    if not CRON_SECRET:
        # Aucun secret configuré → accès toujours refusé (même en DEBUG)
        logger.error("CRON_SECRET non configuré — tous les appels cron sont rejetés")
        return False
    auth = request.headers.get("Authorization", "")
    if auth.startswith("Bearer "):
        return auth[7:] == CRON_SECRET
    return request.GET.get("secret") == CRON_SECRET


@csrf_exempt
@require_GET
def cron_expire_ads(request: HttpRequest) -> JsonResponse:
    """Archive les annonces expirées. Fréquence : 1×/heure."""
    if not _check_auth(request):
        return JsonResponse({"error": "Unauthorized"}, status=401)
    try:
        from ads.tasks import expire_ads
        result = expire_ads()
        logger.info("cron_expire_ads: %s", result)
        return JsonResponse({"ok": True, "result": str(result)})
    except Exception as e:
        logger.exception("cron_expire_ads failed: %s", e)
        return JsonResponse({"ok": False, "error": str(e)}, status=500)


@csrf_exempt
@require_GET
def cron_notify_24h(request: HttpRequest) -> JsonResponse:
    """Email J-1 aux annonceurs. Fréquence : 1×/heure."""
    if not _check_auth(request):
        return JsonResponse({"error": "Unauthorized"}, status=401)
    try:
        from ads.tasks import notify_expiring_soon_24h
        result = notify_expiring_soon_24h()
        logger.info("cron_notify_24h: %s", result)
        return JsonResponse({"ok": True, "result": str(result)})
    except Exception as e:
        logger.exception("cron_notify_24h failed: %s", e)
        return JsonResponse({"ok": False, "error": str(e)}, status=500)


@csrf_exempt
@require_GET
def cron_notify_1h(request: HttpRequest) -> JsonResponse:
    """Email H-1 aux annonceurs. Fréquence : 1×/15 min."""
    if not _check_auth(request):
        return JsonResponse({"error": "Unauthorized"}, status=401)
    try:
        from ads.tasks import notify_expiring_soon_1h
        result = notify_expiring_soon_1h()
        logger.info("cron_notify_1h: %s", result)
        return JsonResponse({"ok": True, "result": str(result)})
    except Exception as e:
        logger.exception("cron_notify_1h failed: %s", e)
        return JsonResponse({"ok": False, "error": str(e)}, status=500)


@csrf_exempt
@require_GET
def cron_promote_boosts(request: HttpRequest) -> JsonResponse:
    """Remet les annonces boostées en tête. Fréquence : 1×/2h minimum."""
    if not _check_auth(request):
        return JsonResponse({"error": "Unauthorized"}, status=401)
    try:
        from ads.tasks import promote_boosted_ads
        result = promote_boosted_ads()
        logger.info("cron_promote_boosts: %s", result)
        return JsonResponse({"ok": True, "result": str(result)})
    except Exception as e:
        logger.exception("cron_promote_boosts failed: %s", e)
        return JsonResponse({"ok": False, "error": str(e)}, status=500)
