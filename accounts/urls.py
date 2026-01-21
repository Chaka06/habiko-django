from django.urls import path
from . import views

app_name = "accounts"

urlpatterns = [
    path("profile/", views.profile_edit, name="profile_edit"),
    path("u/<str:username>/", views.public_profile, name="public_profile"),
    path("password/change/", views.password_change, name="password_change"),
    path("password/change/confirm/", views.password_change_confirm, name="password_change_confirm"),
    path(
        "password/change/resend/", views.resend_password_change_code, name="password_change_resend"
    ),
    path("validate-profile/<int:profile_id>/", views.validate_profile, name="validate_profile"),
]
