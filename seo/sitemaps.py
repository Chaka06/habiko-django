from django.contrib.sitemaps import Sitemap
from django.urls import reverse
from django.conf import settings
from ads.models import Ad, City

# Forcer le domaine HTTPS pour le sitemap
SITEMAP_DOMAIN = 'https://ci-habiko.com'


class StaticSitemap(Sitemap):
    changefreq = "daily"
    priority = 1.0  # Page d'accueil = priorité maximale
    protocol = 'https'  # Forcer HTTPS pour toutes les URLs

    def items(self):
        return [
            "landing",  # core.urls name="landing" - Page d'accueil
            "ad_list",  # ads.urls name="ad_list" - Liste des annonces
            "post",  # core.urls name="post" - Publier une annonce
            "legal_tos",  # core.urls - CGU
            "legal_privacy",  # core.urls - Confidentialité
            "legal_content_policy",  # core.urls - Politique de contenu
        ]

    def location(self, item):
        if item == "landing":
            return "/"  # Page d'accueil
        return reverse(item)
    
    def lastmod(self, item):
        # Retourner la date actuelle pour indiquer que le contenu est à jour
        from django.utils import timezone
        return timezone.now()


class AdSitemap(Sitemap):
    changefreq = "daily"
    priority = 0.9
    protocol = 'https'  # Forcer HTTPS pour toutes les URLs

    def items(self):
        return Ad.objects.filter(status=Ad.Status.APPROVED).select_related("city")

    def location(self, obj: Ad):
        return f"/ads/{obj.slug}"

    def lastmod(self, obj: Ad):
        return obj.updated_at


class CitySitemap(Sitemap):
    changefreq = "weekly"
    priority = 0.7
    protocol = 'https'  # Forcer HTTPS pour toutes les URLs

    def items(self):
        return City.objects.all()

    def location(self, obj: City):
        return f"/ads?city={obj.slug}"


class CategorySitemap(Sitemap):
    changefreq = "weekly"
    priority = 0.6
    protocol = 'https'  # Forcer HTTPS pour toutes les URLs

    def items(self):
        return [
            "maisons_appartements",
            "villas_residences",
            "terrains",
            "locations",
        ]

    def location(self, item):
        return f"/ads?category={item}"


class CityCategorySitemap(Sitemap):
    changefreq = "weekly"
    priority = 0.8
    protocol = 'https'  # Forcer HTTPS pour toutes les URLs

    def items(self):
        cities = City.objects.all()
        categories = ["maisons_appartements", "villas_residences", "terrains", "locations"]
        items = []
        for city in cities:
            for category in categories:
                items.append((city.slug, category))
        return items

    def location(self, item):
        city_slug, category = item
        return f"/ads?city={city_slug}&category={category}"
