from django.urls import path
from . import views

urlpatterns = [
    # ── Auth ───────────────────────────────────────────────────────────────────
    path("auth/login/",           views.api_login,           name="api_login"),
    path("auth/register/",        views.api_register,        name="api_register"),
    path("auth/logout/",          views.api_logout,          name="api_logout"),
    path("auth/me/",              views.api_me,              name="api_me"),
    path("auth/password/change/", views.api_change_password, name="api_change_password"),

    # ── Annonces ───────────────────────────────────────────────────────────────
    path("ads/",                  views.api_ads_list,        name="api_ads_list"),
    path("ads/mine/",             views.api_my_ads,          name="api_my_ads"),
    path("ads/<int:pk>/",         views.api_ad_detail,       name="api_ad_detail"),
    path("ads/<int:pk>/delete/",  views.api_delete_ad,       name="api_delete_ad"),
    path("cities/",               views.api_cities,          name="api_cities"),

    # ── Favoris ────────────────────────────────────────────────────────────────
    path("favorites/",               views.api_favorites,        name="api_favorites"),
    path("favorites/toggle/<int:pk>/", views.api_toggle_favorite, name="api_toggle_favorite"),
    path("favorites/check/<int:pk>/",  views.api_check_favorite,  name="api_check_favorite"),

    # ── Paiements ──────────────────────────────────────────────────────────────
    path("payments/history/",      views.api_payment_history, name="api_payment_history"),
    path("payments/promo/check/",  views.api_check_promo,     name="api_check_promo"),
]
