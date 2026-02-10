from django.urls import path
from . import views, admin_views


urlpatterns = [
    path("", views.ad_list, name="ad_list"),
    path("api/search-suggestions/", views.search_suggestions, name="ad_search_suggestions"),
    path("<slug:slug>/", views.ad_detail, name="ad_detail"),
    # URLs pour actions admin
    path("admin/approve/<int:ad_id>/", admin_views.approve_ad, name="ads_ad_approve"),
    path("admin/reject/<int:ad_id>/", admin_views.reject_ad, name="ads_ad_reject"),
]
