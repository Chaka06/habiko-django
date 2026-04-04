from django.urls import path
from . import views
from .cookie_consent import cookie_consent
from . import cron_views


urlpatterns = [
    path("", views.landing, name="landing"),
    path("post/", views.post, name="post"),
    path("edit/<int:ad_id>/", views.edit_ad, name="edit_ad"),
    path("delete/<int:ad_id>/", views.delete_ad, name="delete_ad"),
    path("dashboard/", views.dashboard, name="dashboard"),
    # Légal
    path("legal/tos/", views.legal_tos, name="legal_tos"),
    path("legal/privacy/", views.legal_privacy, name="legal_privacy"),
    path("legal/content-policy/", views.legal_content_policy, name="legal_content_policy"),
    # Report
    path("report/<int:ad_id>/", views.report_ad, name="report_ad"),
    # Cookies
    path("api/cookie-consent/", cookie_consent, name="cookie_consent"),
    # Favicon à la racine pour Google
    path("favicon.ico", views.favicon, name="favicon"),
    # Health check pour Vercel, Docker et les outils de monitoring
    path("health/", views.health_check, name="health_check"),
    # Cron jobs (appelés par Vercel Cron + cron-job.org)
    path("cron/expire-ads/",    cron_views.cron_expire_ads,    name="cron_expire_ads"),
    path("cron/notify-24h/",    cron_views.cron_notify_24h,    name="cron_notify_24h"),
    path("cron/notify-1h/",     cron_views.cron_notify_1h,     name="cron_notify_1h"),
    path("cron/promote-boosts/", cron_views.cron_promote_boosts, name="cron_promote_boosts"),
    path("cron/purge-expired-ads/", cron_views.cron_purge_expired_ads, name="cron_purge_expired_ads"),
]
