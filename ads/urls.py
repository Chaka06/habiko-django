from django.urls import path, re_path
from . import views, admin_views


# Mapping catégorie → slug URL (jedolo-style clean URLs)
_CAT_SLUG_MAP = {
    "escort-girl": "escorte_girl",
    "escort-boy": "escorte_boy",
    "transgenre": "transgenre",
}

# Générer dynamiquement les patterns /ads/<cat-slug>/ et /ads/<cat-slug>-<city-slug>/
_seo_patterns = []
for _url_slug, _cat in _CAT_SLUG_MAP.items():
    # /ads/escort-girl/
    _seo_patterns.append(
        path(
            f"{_url_slug}/",
            views.ad_list_seo,
            {"city_slug": "", "category": _cat},
            name=f"ad_list_cat_{_cat}",
        )
    )
    # /ads/escort-girl-<city-slug>/
    _seo_patterns.append(
        re_path(
            rf"^{_url_slug}-(?P<city_slug>[\w-]+)/$",
            views.ad_list_seo,
            {"category": _cat},
            name=f"ad_list_cat_{_cat}_city",
        )
    )

# /ads/bizi-<city-slug>/  — toutes catégories pour une ville
_seo_patterns.append(
    re_path(
        r"^bizi-(?P<city_slug>[\w-]+)/$",
        views.ad_list_seo,
        {"category": ""},
        name="ad_list_city",
    )
)

urlpatterns = [
    path("", views.ad_list, name="ad_list"),
    path("api/search-suggestions/", views.search_suggestions, name="ad_search_suggestions"),
    path("favorites/", views.favorites_list, name="favorites_list"),
    path("favorites/toggle/<int:ad_id>/", views.toggle_favorite, name="toggle_favorite"),
    # URLs SEO propres (avant le catch-all <slug>)
    *_seo_patterns,
    path("<slug:slug>/", views.ad_detail, name="ad_detail"),
    path("<slug:slug>/record-view/", views.record_ad_view, name="record_ad_view"),
    # Crons Vercel
    path("cron/watermarks/", views.cron_apply_watermarks, name="cron_apply_watermarks"),
    path("cron/bump/", views.cron_bump_ads, name="cron_bump_ads"),
    # URLs pour actions admin
    path("admin/approve/<int:ad_id>/", admin_views.approve_ad, name="ads_ad_approve"),
    path("admin/reject/<int:ad_id>/", admin_views.reject_ad, name="ads_ad_reject"),
]
