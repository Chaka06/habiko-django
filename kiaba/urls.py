"""
URL configuration for kiaba project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.1/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""

from django.contrib import admin
from django.urls import include, path, re_path
from django.conf import settings
from django.conf.urls.static import static
from django.contrib.sitemaps.views import sitemap
from seo.sitemaps import StaticSitemap, AdSitemap, CitySitemap, CategorySitemap, CityCategorySitemap
from django.views.static import serve
from django.http import HttpRequest, HttpResponse

# Domaine canonique du sitemap (indépendant du framework Sites)
SITEMAP_DOMAIN = "ci-kiaba.com"


def sitemap_https(request: HttpRequest) -> HttpResponse:
    """Vue personnalisée pour forcer HTTPS et le domaine ci-kiaba.com dans le sitemap."""
    request.META["wsgi.url_scheme"] = "https"
    request.META["HTTP_X_FORWARDED_PROTO"] = "https"
    # Forcer le host pour que toutes les URLs du sitemap soient en https://ci-kiaba.com/...
    request.META["HTTP_HOST"] = SITEMAP_DOMAIN
    return sitemap(
        request,
        {
            "static": StaticSitemap,
            "ads": AdSitemap,
            "cities": CitySitemap,
            "categories": CategorySitemap,
            "city_categories": CityCategorySitemap,
        }
    )

urlpatterns = [
    path("admin/", admin.site.urls),
    path("auth/", include("allauth.urls")),
    path("accounts/", include("accounts.urls")),
    path("", include("core.urls")),
    path("ads/", include("ads.urls")),
    path("", include("seo.urls")),
    path(
        "sitemap.xml",
        sitemap_https,
        name="django.contrib.sitemaps.views.sitemap",
    ),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
else:
    # In production, serve media files through WhiteNoise
    urlpatterns += [
        re_path(r"^media/(?P<path>.*)$", serve, {"document_root": settings.MEDIA_ROOT}),
    ]

# Handlers d'erreur pour une réponse propre (404/500) et une meilleure indexation
handler404 = "core.views.page_not_found_view"
handler500 = "core.views.server_error_view"
