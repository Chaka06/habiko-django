from ads.models import Ad, City
from django.conf import settings
from django.core.cache import cache
from django.db import models

# Clés de cache partagées avec ads/views (invalider quand le nombre d'annonces change)
CACHE_KEY_TOTAL_ADS = "total_approved_ads"
CACHE_KEY_POPULAR_CITIES = "popular_cities_footer"
CACHE_TTL = 300  # 5 min


def invalidate_site_metrics_cache():
    """À appeler après approbation/rejet/archivage d'annonces pour rafraîchir le footer et les compteurs."""
    cache.delete(CACHE_KEY_TOTAL_ADS)
    cache.delete(CACHE_KEY_POPULAR_CITIES)


def site_metrics(request):
    """Expose site-wide lightweight metrics to templates (mis en cache pour limiter les requêtes)."""
    total_approved_ads = cache.get(CACHE_KEY_TOTAL_ADS)
    if total_approved_ads is None:
        try:
            total_approved_ads = Ad.objects.filter(status=Ad.Status.APPROVED, image_processing_done=True).count()
            cache.set(CACHE_KEY_TOTAL_ADS, total_approved_ads, CACHE_TTL)
        except Exception:
            total_approved_ads = 0

    popular_cities = cache.get(CACHE_KEY_POPULAR_CITIES)
    if popular_cities is None:
        try:
            popular_cities = list(
                City.objects.filter(ad__status=Ad.Status.APPROVED, ad__image_processing_done=True)
                .annotate(ad_count=models.Count("ad"))
                .filter(ad_count__gt=0)
                .order_by("-ad_count")[:6]
            )
            cache.set(CACHE_KEY_POPULAR_CITIES, popular_cities, CACHE_TTL)
        except Exception:
            popular_cities = []

    return {
        "total_approved_ads": total_approved_ads,
        "GA_MEASUREMENT_ID": getattr(settings, "GA_MEASUREMENT_ID", None),
        "ADSENSE_PUBLISHER_ID": getattr(settings, "ADSENSE_PUBLISHER_ID", None),
        "ADSENSE_ENABLED": getattr(settings, "ADSENSE_ENABLED", False),
        "popular_cities_footer": popular_cities,
        "ENABLE_AGE_GATE": getattr(settings, "ENABLE_AGE_GATE", False),
    }
