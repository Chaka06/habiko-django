from django.urls import path
from . import views
from .cookie_consent import cookie_consent


urlpatterns = [
    path("", views.landing, name="landing"),
    path("post/", views.post, name="post"),
    path("edit/<int:ad_id>/", views.edit_ad, name="edit_ad"),
    path("dashboard/", views.dashboard, name="dashboard"),
    # Légal
    path("legal/tos", views.legal_tos, name="legal_tos"),
    path("legal/privacy", views.legal_privacy, name="legal_privacy"),
    path("legal/content-policy", views.legal_content_policy, name="legal_content_policy"),
    # Report
    path("report/<int:ad_id>", views.report_ad, name="report_ad"),
    # Cookies
    path("api/cookie-consent/", cookie_consent, name="cookie_consent"),
    # Favicon à la racine pour Google
    path("favicon.ico", views.favicon, name="favicon"),
]
