from django.urls import path
from . import views


urlpatterns = [
    path("robots.txt", views.robots_txt, name="robots_txt"),
    path("ads.txt", views.ads_txt, name="ads_txt"),
    path("googleb96ecc9cfd50e4a1.html", views.google_verification, name="google_verification"),
]
