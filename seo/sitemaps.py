from django.contrib.sitemaps import Sitemap
from django.urls import reverse
from django.conf import settings
from ads.models import Ad, City

# Domaine canonique : la vue Django passe get_current_site(request) à get_urls(), donc
# le domaine vient de la table Site (souvent example.com). On force ci-kiaba.com en
# surchargeant get_domain() dans une base commune.
SITEMAP_DOMAIN = "ci-kiaba.com"

# Catégories réelles du modèle Ad (escorte, etc.)
AD_CATEGORY_SLUGS = [c.value for c in Ad.Category]


class KiabaSitemapBase(Sitemap):
    """Base qui force le domaine ci-kiaba.com (Django utilise sinon get_current_site(request).domain)."""

    def get_domain(self, site=None):
        return SITEMAP_DOMAIN


class StaticSitemap(KiabaSitemapBase):
    changefreq = "daily"
    priority = 1.0
    protocol = "https"

    def items(self):
        return [
            "landing",
            "ad_list",
            "post",
            "legal_tos",
            "legal_privacy",
            "legal_content_policy",
        ]

    def location(self, item):
        if item == "landing":
            return "/"
        return reverse(item)

    def lastmod(self, item):
        from django.utils import timezone
        return timezone.now()


class AdSitemap(KiabaSitemapBase):
    changefreq = "daily"
    priority = 0.9
    protocol = "https"
    limit = 5000  # max URLs par section sitemap (Google recommande ≤ 50 000)

    def items(self):
        return Ad.objects.filter(status=Ad.Status.APPROVED).select_related("city").order_by("-updated_at")

    def location(self, obj: Ad):
        return f"/ads/{obj.slug}"

    def lastmod(self, obj: Ad):
        return obj.updated_at


class CitySitemap(KiabaSitemapBase):
    changefreq = "weekly"
    priority = 0.7
    protocol = "https"

    def items(self):
        return City.objects.all().order_by("name")

    def location(self, obj: City):
        return f"/ads?city={obj.slug}"


class CategorySitemap(KiabaSitemapBase):
    changefreq = "weekly"
    priority = 0.6
    protocol = "https"

    def items(self):
        return AD_CATEGORY_SLUGS

    def location(self, item):
        return f"/ads?category={item}"


class CityCategorySitemap(KiabaSitemapBase):
    """Villes × catégories : uniquement les combinaisons qui ont des annonces approuvées."""
    changefreq = "weekly"
    priority = 0.8
    protocol = "https"
    limit = 5000

    def items(self):
        from django.db.models import Count
        qs = (
            City.objects.filter(ad__status=Ad.Status.APPROVED)
            .annotate(n=Count("ad"))
            .filter(n__gt=0)
            .order_by("slug")
        )
        items = []
        for city in qs:
            for cat in AD_CATEGORY_SLUGS:
                items.append((city.slug, cat))
        return items

    def location(self, item):
        city_slug, category = item
        return f"/ads?city={city_slug}&category={category}"
