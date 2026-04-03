from django.urls import path
from . import views

app_name = "payments"

urlpatterns = [
    path("form/",                    views.pay_form,           name="pay_form"),
    path("for/<int:ad_id>/",         views.pay_for_existing_ad, name="pay_for_ad"),
    path("initiate/",                views.initiate_payment,    name="initiate"),
    path("return/<uuid:deposit_id>/", views.payment_return,     name="return"),
    path("status/<uuid:deposit_id>/", views.payment_status,     name="status"),
    path("webhook/geniuspay/",        views.geniuspay_webhook,  name="webhook"),
    path("boost/<int:ad_id>/",        views.boost_ad,           name="boost_ad"),
    path("renew/<int:ad_id>/",        views.renew_ad,           name="renew_ad"),
    path("promo/check/",              views.check_promo_code,   name="check_promo"),
]
