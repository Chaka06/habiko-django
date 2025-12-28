from django.urls import path
from . import views

app_name = "accounts"

urlpatterns = [
    path("profile/", views.profile_edit, name="profile_edit"),
    path("password/change/", views.password_change, name="password_change"),
    path("password/change/confirm/", views.password_change_confirm, name="password_change_confirm"),
    path(
        "password/change/resend/", views.resend_password_change_code, name="password_change_resend"
    ),
    path("validate-profile/<int:profile_id>/", views.validate_profile, name="validate_profile"),
    # Compte et crédits
    path("account/", views.account_balance, name="account_balance"),
    path("account/recharge/", views.recharge_account, name="recharge_account"),
    path("account/boost/<int:ad_id>/", views.boost_ad, name="boost_ad"),
    # Paiements CinetPay
    path("payment/cinetpay/notify/", views.cinetpay_notify, name="cinetpay_notify"),
    path("payment/cinetpay/return/", views.cinetpay_return, name="cinetpay_return"),
]
