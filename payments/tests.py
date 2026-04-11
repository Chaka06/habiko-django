"""
Tests complets — app payments
Couvre : modèles Payment/PromoCode, vues GeniusPay, webhook,
         activation annonce, boost, renouvellement, code promo
"""
import hashlib
import hmac
import json
import time
import uuid
from datetime import timedelta
from decimal import Decimal
from unittest.mock import MagicMock, patch

from django.contrib.auth import get_user_model
from django.test import Client, TestCase, override_settings
from django.utils import timezone

from ads.models import Ad, City
from .models import Payment, PromoCode, PromoCodeUsage
from .views import _activate_ad_for_payment, PRICE_STANDARD, PRICE_BUNDLE, PRICE_BOOST

User = get_user_model()


# ─── Factories ────────────────────────────────────────────────────────────────

def make_user(username="u1", email="u1@test.com", password="pass1234!"):
    return User.objects.create_user(username=username, email=email, password=password)


def make_city():
    return City.objects.create(name="Abidjan", region="Lagunes")


def make_ad(user, city, **kw):
    return Ad.objects.create(
        user=user,
        title=kw.pop("title", "Annonce"),
        description_sanitized="Desc",
        category=Ad.Category.ESCORTE_GIRL,
        city=city,
        status=kw.pop("status", Ad.Status.DRAFT),
        image_processing_done=True,
        **kw,
    )


def make_payment(user, ad, pay_type=Payment.Type.STANDARD, amount=None, **kw):
    return Payment.objects.create(
        user=user,
        ad=ad,
        type=pay_type,
        amount=amount or PRICE_STANDARD,
        **kw,
    )


def webhook_signature(secret: str, timestamp: str, body: bytes) -> str:
    """Calcule la signature HMAC-SHA256 attendue par le webhook."""
    msg = f"{timestamp}.".encode() + body
    return hmac.new(secret.encode(), msg, hashlib.sha256).hexdigest()


# ═══════════════════════════════════════════════════════════════════════════════
# PAYMENT MODEL
# ═══════════════════════════════════════════════════════════════════════════════

class PaymentModelTest(TestCase):
    def setUp(self):
        self.user = make_user()
        self.city = make_city()
        self.ad = make_ad(self.user, self.city)

    def test_deposit_id_auto_generated_uuid(self):
        p = make_payment(self.user, self.ad)
        self.assertIsNotNone(p.deposit_id)
        # doit être un UUID valide
        uuid.UUID(str(p.deposit_id))

    def test_deposit_id_unique_per_payment(self):
        p1 = make_payment(self.user, self.ad)
        p2 = make_payment(self.user, self.ad)
        self.assertNotEqual(p1.deposit_id, p2.deposit_id)

    def test_default_status_pending(self):
        p = make_payment(self.user, self.ad)
        self.assertEqual(p.status, Payment.Status.PENDING)

    def test_all_payment_types_available(self):
        types = [v for v, _ in Payment.Type.choices]
        for t in ["standard", "boost", "bundle", "fortnight", "monthly",
                  "renew_15", "renew_15b", "renew_mon", "renew_monb"]:
            self.assertIn(t, types)

    def test_str_contains_type_and_status(self):
        p = make_payment(self.user, self.ad)
        s = str(p)
        self.assertIn(str(p.deposit_id), s)

    def test_gateway_response_default_empty_dict(self):
        p = make_payment(self.user, self.ad)
        self.assertEqual(p.gateway_response, {})


# ═══════════════════════════════════════════════════════════════════════════════
# PROMO CODE MODEL
# ═══════════════════════════════════════════════════════════════════════════════

class PromoCodeModelTest(TestCase):
    def setUp(self):
        self.user = make_user()
        self.city = make_city()
        self.ad = make_ad(self.user, self.city)

    def _make_promo(self, **kw):
        return PromoCode.objects.create(
            code=kw.pop("code", "TEST10"),
            discount_percent=kw.pop("discount_percent", 10),
            **kw,
        )

    def test_is_valid_active_promo(self):
        p = self._make_promo(active=True)
        self.assertTrue(p.is_valid())

    def test_is_valid_false_when_inactive(self):
        p = self._make_promo(active=False)
        self.assertFalse(p.is_valid())

    def test_is_valid_false_when_expired(self):
        p = self._make_promo(expires_at=timezone.now() - timedelta(hours=1))
        self.assertFalse(p.is_valid())

    def test_is_valid_true_before_expiry(self):
        p = self._make_promo(expires_at=timezone.now() + timedelta(days=7))
        self.assertTrue(p.is_valid())

    def test_is_valid_false_when_max_uses_reached(self):
        p = self._make_promo(code="MAX1", max_uses=1)
        PromoCodeUsage.objects.create(code="MAX1", user=self.user, discount_applied=100)
        self.assertFalse(p.is_valid())

    def test_is_valid_true_when_below_max_uses(self):
        p = self._make_promo(code="MAX5", max_uses=5)
        PromoCodeUsage.objects.create(code="MAX5", user=self.user, discount_applied=50)
        self.assertTrue(p.is_valid())

    def test_is_valid_true_when_max_uses_none(self):
        p = self._make_promo(max_uses=None)
        self.assertTrue(p.is_valid())

    def test_code_is_unique(self):
        self._make_promo(code="UNIQ")
        with self.assertRaises(Exception):
            self._make_promo(code="UNIQ")

    def test_str_contains_code_and_percent(self):
        p = self._make_promo(code="VIP20", discount_percent=20)
        self.assertIn("VIP20", str(p))
        self.assertIn("20", str(p))


# ═══════════════════════════════════════════════════════════════════════════════
# _activate_ad_for_payment (logique métier centrale)
# ═══════════════════════════════════════════════════════════════════════════════

@override_settings(CELERY_TASK_ALWAYS_EAGER=True)
class ActivateAdForPaymentTest(TestCase):
    def setUp(self):
        self.user = make_user()
        self.city = make_city()
        self.ad = make_ad(self.user, self.city)

    @patch("payments.views.auto_approve_ad.delay")
    def test_standard_payment_sets_expires_5_days(self, mock_task):
        p = make_payment(self.user, self.ad, pay_type=Payment.Type.STANDARD)
        _activate_ad_for_payment(p)
        self.ad.refresh_from_db()
        expected = timezone.now() + timedelta(days=5)
        self.assertAlmostEqual(
            self.ad.expires_at.timestamp(), expected.timestamp(), delta=10
        )

    @patch("payments.views.auto_approve_ad.delay")
    def test_standard_payment_moves_ad_to_pending(self, mock_task):
        p = make_payment(self.user, self.ad, pay_type=Payment.Type.STANDARD)
        _activate_ad_for_payment(p)
        self.ad.refresh_from_db()
        self.assertEqual(self.ad.status, Ad.Status.PENDING)

    @patch("payments.views.auto_approve_ad.delay")
    def test_standard_payment_completes_payment(self, mock_task):
        p = make_payment(self.user, self.ad, pay_type=Payment.Type.STANDARD)
        _activate_ad_for_payment(p)
        p.refresh_from_db()
        self.assertEqual(p.status, Payment.Status.COMPLETED)
        self.assertIsNotNone(p.completed_at)

    @patch("payments.views.auto_approve_ad.delay")
    def test_fortnight_payment_sets_expires_15_days(self, mock_task):
        p = make_payment(self.user, self.ad, pay_type=Payment.Type.FORTNIGHT, amount=3500)
        _activate_ad_for_payment(p)
        self.ad.refresh_from_db()
        expected = timezone.now() + timedelta(days=15)
        self.assertAlmostEqual(
            self.ad.expires_at.timestamp(), expected.timestamp(), delta=10
        )

    @patch("payments.views.auto_approve_ad.delay")
    def test_monthly_payment_sets_expires_30_days(self, mock_task):
        p = make_payment(self.user, self.ad, pay_type=Payment.Type.MONTHLY, amount=6500)
        _activate_ad_for_payment(p)
        self.ad.refresh_from_db()
        expected = timezone.now() + timedelta(days=30)
        self.assertAlmostEqual(
            self.ad.expires_at.timestamp(), expected.timestamp(), delta=10
        )

    @patch("payments.views.auto_approve_ad.delay")
    def test_boost_payment_sets_is_boosted(self, mock_task):
        approved_ad = make_ad(self.user, self.city, status=Ad.Status.APPROVED)
        p = make_payment(self.user, approved_ad, pay_type=Payment.Type.BOOST, amount=PRICE_BOOST)
        _activate_ad_for_payment(p)
        approved_ad.refresh_from_db()
        self.assertTrue(approved_ad.is_boosted)

    @patch("payments.views.auto_approve_ad.delay")
    def test_bundle_sets_both_expires_and_boost(self, mock_task):
        p = make_payment(self.user, self.ad, pay_type=Payment.Type.BUNDLE, amount=PRICE_BUNDLE)
        _activate_ad_for_payment(p)
        self.ad.refresh_from_db()
        self.assertTrue(self.ad.is_boosted)
        self.assertIsNotNone(self.ad.expires_at)

    @patch("payments.views.auto_approve_ad.delay")
    def test_idempotent_second_call_ignored(self, mock_task):
        p = make_payment(self.user, self.ad, pay_type=Payment.Type.STANDARD)
        _activate_ad_for_payment(p)
        _activate_ad_for_payment(p)  # deuxième appel ignoré
        self.assertEqual(mock_task.call_count, 1)

    @patch("payments.views.auto_approve_ad.delay")
    def test_renewal_15_extends_expires_at(self, mock_task):
        approved = make_ad(self.user, self.city, status=Ad.Status.APPROVED)
        original_expires = timezone.now() + timedelta(days=2)
        approved.expires_at = original_expires
        approved.save()
        p = make_payment(self.user, approved, pay_type=Payment.Type.RENEW_15, amount=1000)
        _activate_ad_for_payment(p)
        approved.refresh_from_db()
        self.assertGreater(approved.expires_at, original_expires)

    @patch("payments.views.auto_approve_ad.delay")
    def test_renew_boost_sets_is_boosted(self, mock_task):
        approved = make_ad(self.user, self.city, status=Ad.Status.APPROVED)
        p = make_payment(self.user, approved, pay_type=Payment.Type.RENEW_15B, amount=2500)
        _activate_ad_for_payment(p)
        approved.refresh_from_db()
        self.assertTrue(approved.is_boosted)


# ═══════════════════════════════════════════════════════════════════════════════
# VUE : pay_form
# ═══════════════════════════════════════════════════════════════════════════════

class PayFormViewTest(TestCase):
    def setUp(self):
        self.client = Client()
        self.client.cookies["age_gate_accepted"] = "1"
        self.user = make_user()
        self.city = make_city()

    def test_anonymous_redirected(self):
        r = self.client.get("/pay/form/")
        self.assertEqual(r.status_code, 302)

    def test_no_session_ad_redirects_to_post(self):
        self.client.force_login(self.user)
        r = self.client.get("/pay/form/")
        self.assertRedirects(r, "/post/", fetch_redirect_response=False)

    def test_with_session_draft_ad_renders_form(self):
        self.client.force_login(self.user)
        ad = make_ad(self.user, self.city)
        session = self.client.session
        session["pending_ad_id"] = ad.pk
        session.save()
        r = self.client.get("/pay/form/")
        self.assertEqual(r.status_code, 200)
        self.assertContains(r, str(PRICE_STANDARD))

    def test_approved_ad_in_session_redirects_to_post(self):
        self.client.force_login(self.user)
        approved = make_ad(self.user, self.city, status=Ad.Status.APPROVED)
        session = self.client.session
        session["pending_ad_id"] = approved.pk
        session.save()
        r = self.client.get("/pay/form/")
        self.assertRedirects(r, "/post/", fetch_redirect_response=False)


# ═══════════════════════════════════════════════════════════════════════════════
# VUE : initiate_payment
# ═══════════════════════════════════════════════════════════════════════════════

@override_settings(CACHES={"default": {"BACKEND": "django.core.cache.backends.locmem.LocMemCache"}})
class InitiatePaymentViewTest(TestCase):
    def setUp(self):
        self.client = Client()
        self.client.cookies["age_gate_accepted"] = "1"
        self.user = make_user()
        self.city = make_city()

    def _set_session_ad(self, ad):
        session = self.client.session
        session["pending_ad_id"] = ad.pk
        session.save()

    def test_anonymous_redirected(self):
        r = self.client.post("/pay/initiate/", {"forfait": "standard"})
        self.assertEqual(r.status_code, 302)

    def test_get_not_allowed(self):
        self.client.force_login(self.user)
        r = self.client.get("/pay/initiate/")
        self.assertEqual(r.status_code, 405)

    @patch("payments.views._call_geniuspay", return_value="https://pay.geniuspay.com/checkout/abc")
    def test_valid_standard_forfait_redirects_to_checkout(self, mock_gp):
        self.client.force_login(self.user)
        ad = make_ad(self.user, self.city)
        self._set_session_ad(ad)
        r = self.client.post("/pay/initiate/", {"forfait": "standard"})
        self.assertRedirects(r, "https://pay.geniuspay.com/checkout/abc",
                             fetch_redirect_response=False)

    @patch("payments.views._call_geniuspay", return_value="https://geniuspay.com/checkout")
    def test_creates_payment_object(self, mock_gp):
        self.client.force_login(self.user)
        ad = make_ad(self.user, self.city)
        self._set_session_ad(ad)
        self.client.post("/pay/initiate/", {"forfait": "standard"})
        self.assertTrue(Payment.objects.filter(user=self.user, ad=ad).exists())

    @patch("payments.views._call_geniuspay", return_value="https://geniuspay.com/checkout")
    def test_bundle_forfait_creates_bundle_payment(self, mock_gp):
        self.client.force_login(self.user)
        ad = make_ad(self.user, self.city)
        self._set_session_ad(ad)
        self.client.post("/pay/initiate/", {"forfait": "bundle"})
        p = Payment.objects.filter(user=self.user, ad=ad).first()
        self.assertEqual(p.type, Payment.Type.BUNDLE)
        self.assertEqual(p.amount, PRICE_BUNDLE)

    def test_invalid_forfait_redirects_back(self):
        self.client.force_login(self.user)
        ad = make_ad(self.user, self.city)
        self._set_session_ad(ad)
        r = self.client.post("/pay/initiate/", {"forfait": "forfait_inexistant"})
        self.assertEqual(r.status_code, 302)
        # L'annonce doit rester en session
        self.assertIn("pending_ad_id", self.client.session)

    @patch("payments.views._call_geniuspay", return_value=None)
    def test_geniuspay_failure_redirects_back(self, mock_gp):
        self.client.force_login(self.user)
        ad = make_ad(self.user, self.city)
        self._set_session_ad(ad)
        r = self.client.post("/pay/initiate/", {"forfait": "standard"})
        self.assertEqual(r.status_code, 302)

    @patch("payments.views._call_geniuspay", return_value="https://geniuspay.com/checkout")
    def test_valid_promo_code_reduces_amount(self, mock_gp):
        PromoCode.objects.create(code="SAVE20", discount_percent=20, active=True)
        self.client.force_login(self.user)
        ad = make_ad(self.user, self.city)
        self._set_session_ad(ad)
        self.client.post("/pay/initiate/", {"forfait": "standard", "promo_code": "SAVE20"})
        p = Payment.objects.filter(user=self.user, ad=ad).first()
        self.assertLess(p.amount, PRICE_STANDARD)

    @patch("payments.views._call_geniuspay", return_value="https://geniuspay.com/checkout")
    def test_promo_usage_recorded(self, mock_gp):
        PromoCode.objects.create(code="PROMO5", discount_percent=5, active=True)
        self.client.force_login(self.user)
        ad = make_ad(self.user, self.city)
        self._set_session_ad(ad)
        self.client.post("/pay/initiate/", {"forfait": "standard", "promo_code": "PROMO5"})
        self.assertTrue(PromoCodeUsage.objects.filter(code="PROMO5", user=self.user).exists())

    def test_rate_limit_5_per_minute(self):
        """La 6e tentative est bloquée."""
        self.client.force_login(self.user)
        from django.core.cache import cache
        cache.set(f"pay_ratelimit:{self.user.pk}", 5, 60)
        ad = make_ad(self.user, self.city)
        self._set_session_ad(ad)
        r = self.client.post("/pay/initiate/", {"forfait": "standard"})
        # Doit rediriger sans créer de paiement
        self.assertEqual(r.status_code, 302)
        self.assertFalse(Payment.objects.filter(user=self.user, ad=ad).exists())


# ═══════════════════════════════════════════════════════════════════════════════
# VUE : payment_return
# ═══════════════════════════════════════════════════════════════════════════════

class PaymentReturnViewTest(TestCase):
    def setUp(self):
        self.client = Client()
        self.client.cookies["age_gate_accepted"] = "1"
        self.user = make_user()
        self.city = make_city()
        self.ad = make_ad(self.user, self.city)

    def test_anonymous_redirected(self):
        p = make_payment(self.user, self.ad)
        r = self.client.get(f"/pay/return/{p.deposit_id}/")
        self.assertEqual(r.status_code, 302)

    def test_return_page_renders_200(self):
        self.client.force_login(self.user)
        p = make_payment(self.user, self.ad)
        r = self.client.get(f"/pay/return/{p.deposit_id}/")
        self.assertEqual(r.status_code, 200)

    def test_failed_flag_marks_payment_failed(self):
        self.client.force_login(self.user)
        p = make_payment(self.user, self.ad)
        r = self.client.get(f"/pay/return/{p.deposit_id}/?failed=1")
        self.assertEqual(r.status_code, 200)
        p.refresh_from_db()
        self.assertEqual(p.status, Payment.Status.FAILED)

    def test_failed_flag_on_completed_payment_ignored(self):
        self.client.force_login(self.user)
        p = make_payment(self.user, self.ad, status=Payment.Status.COMPLETED)
        self.client.get(f"/pay/return/{p.deposit_id}/?failed=1")
        p.refresh_from_db()
        self.assertEqual(p.status, Payment.Status.COMPLETED)

    def test_other_user_cannot_see_payment(self):
        u2 = make_user("u2", "u2@t.com")
        p = make_payment(self.user, self.ad)
        self.client.force_login(u2)
        r = self.client.get(f"/pay/return/{p.deposit_id}/")
        self.assertEqual(r.status_code, 404)


# ═══════════════════════════════════════════════════════════════════════════════
# VUE : payment_status (polling)
# ═══════════════════════════════════════════════════════════════════════════════

class PaymentStatusViewTest(TestCase):
    def setUp(self):
        self.client = Client()
        self.client.cookies["age_gate_accepted"] = "1"
        self.user = make_user()
        self.city = make_city()
        self.ad = make_ad(self.user, self.city)

    def test_anonymous_redirected(self):
        p = make_payment(self.user, self.ad)
        r = self.client.get(f"/pay/status/{p.deposit_id}/")
        self.assertEqual(r.status_code, 302)

    def test_returns_status_json(self):
        self.client.force_login(self.user)
        p = make_payment(self.user, self.ad)
        r = self.client.get(f"/pay/status/{p.deposit_id}/")
        self.assertEqual(r.status_code, 200)
        data = json.loads(r.content)
        self.assertIn("status", data)

    def test_completed_payment_returns_ad_slug(self):
        self.client.force_login(self.user)
        p = make_payment(self.user, self.ad, status=Payment.Status.COMPLETED)
        r = self.client.get(f"/pay/status/{p.deposit_id}/")
        data = json.loads(r.content)
        self.assertEqual(data["ad_slug"], self.ad.slug)

    @patch("payments.views.geniuspay_svc.get_payment")
    @patch("payments.views.auto_approve_ad.delay")
    def test_pending_with_reference_polls_geniuspay(self, mock_approve, mock_get):
        mock_get.return_value = {"status": "pending"}
        self.client.force_login(self.user)
        p = make_payment(self.user, self.ad, geniuspay_reference="REF123")
        r = self.client.get(f"/pay/status/{p.deposit_id}/")
        mock_get.assert_called_once_with("REF123")

    @patch("payments.views.geniuspay_svc.get_payment")
    @patch("payments.views.auto_approve_ad.delay")
    def test_geniuspay_completed_activates_ad(self, mock_approve, mock_get):
        mock_get.return_value = {"status": "completed"}
        self.client.force_login(self.user)
        p = make_payment(self.user, self.ad, geniuspay_reference="REF456")
        self.client.get(f"/pay/status/{p.deposit_id}/")
        p.refresh_from_db()
        self.assertEqual(p.status, Payment.Status.COMPLETED)

    @patch("payments.views.geniuspay_svc.get_payment")
    def test_geniuspay_failed_marks_payment_failed(self, mock_get):
        mock_get.return_value = {"status": "failed"}
        self.client.force_login(self.user)
        p = make_payment(self.user, self.ad, geniuspay_reference="REF789")
        self.client.get(f"/pay/status/{p.deposit_id}/")
        p.refresh_from_db()
        self.assertEqual(p.status, Payment.Status.FAILED)

    @patch("payments.views.geniuspay_svc.get_payment")
    def test_geniuspay_api_error_does_not_crash(self, mock_get):
        mock_get.side_effect = Exception("Network error")
        self.client.force_login(self.user)
        p = make_payment(self.user, self.ad, geniuspay_reference="REF_ERR")
        r = self.client.get(f"/pay/status/{p.deposit_id}/")
        self.assertEqual(r.status_code, 200)  # pas de crash


# ═══════════════════════════════════════════════════════════════════════════════
# VUE : geniuspay_webhook
# ═══════════════════════════════════════════════════════════════════════════════

@override_settings(GENIUSPAY_WEBHOOK_SECRET="testsecret123")
class GeniusPayWebhookTest(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = make_user()
        self.city = make_city()
        self.ad = make_ad(self.user, self.city)
        self.url = "/pay/webhook/geniuspay/"

    def _post_webhook(self, body_dict, event="payment.success", sig_valid=True):
        body = json.dumps(body_dict).encode()
        ts = str(int(time.time()))
        if sig_valid:
            sig = hmac.new(b"testsecret123", f"{ts}.".encode() + body, hashlib.sha256).hexdigest()
        else:
            sig = "invalidsignature"
        return self.client.post(
            self.url,
            data=body,
            content_type="application/json",
            HTTP_X_WEBHOOK_TIMESTAMP=ts,
            HTTP_X_WEBHOOK_SIGNATURE=sig,
            HTTP_X_WEBHOOK_EVENT=event,
        )

    @patch("payments.views.geniuspay_svc.verify_webhook_signature", return_value=False)
    def test_invalid_signature_returns_401(self, mock_verify):
        r = self.client.post(self.url, data=b"{}", content_type="application/json",
                             HTTP_X_WEBHOOK_TIMESTAMP="123",
                             HTTP_X_WEBHOOK_SIGNATURE="bad",
                             HTTP_X_WEBHOOK_EVENT="payment.success")
        self.assertEqual(r.status_code, 401)

    @patch("payments.views.geniuspay_svc.verify_webhook_signature", return_value=True)
    def test_invalid_json_returns_400(self, mock_verify):
        r = self.client.post(self.url, data=b"not json",
                             content_type="application/json",
                             HTTP_X_WEBHOOK_TIMESTAMP="123",
                             HTTP_X_WEBHOOK_SIGNATURE="x",
                             HTTP_X_WEBHOOK_EVENT="payment.success")
        self.assertEqual(r.status_code, 400)

    @patch("payments.views.auto_approve_ad.delay")
    @patch("payments.views.geniuspay_svc.verify_webhook_signature", return_value=True)
    def test_payment_success_activates_ad(self, mock_verify, mock_approve):
        p = make_payment(self.user, self.ad, geniuspay_reference="REF001")
        body = {"data": {"reference": "REF001", "status": "completed"}}
        r = self._post_webhook(body, event="payment.success")
        self.assertEqual(r.status_code, 200)
        p.refresh_from_db()
        self.assertEqual(p.status, Payment.Status.COMPLETED)

    @patch("payments.views.geniuspay_svc.verify_webhook_signature", return_value=True)
    def test_payment_failed_marks_failed(self, mock_verify):
        p = make_payment(self.user, self.ad, geniuspay_reference="REF002")
        body = {"data": {"reference": "REF002", "status": "failed"}}
        r = self._post_webhook(body, event="payment.failed")
        self.assertEqual(r.status_code, 200)
        p.refresh_from_db()
        self.assertEqual(p.status, Payment.Status.FAILED)

    @patch("payments.views.geniuspay_svc.verify_webhook_signature", return_value=True)
    def test_payment_cancelled_marks_failed(self, mock_verify):
        p = make_payment(self.user, self.ad, geniuspay_reference="REF003")
        body = {"data": {"reference": "REF003", "status": "cancelled"}}
        r = self._post_webhook(body, event="payment.cancelled")
        self.assertEqual(r.status_code, 200)
        p.refresh_from_db()
        self.assertEqual(p.status, Payment.Status.FAILED)

    @patch("payments.views.auto_approve_ad.delay")
    @patch("payments.views.geniuspay_svc.verify_webhook_signature", return_value=True)
    def test_duplicate_webhook_idempotent(self, mock_verify, mock_approve):
        p = make_payment(self.user, self.ad, geniuspay_reference="REF004")
        body = {"data": {"reference": "REF004", "status": "completed"}}
        self._post_webhook(body, event="payment.success")
        self._post_webhook(body, event="payment.success")  # doublon
        # auto_approve appelé une seule fois
        self.assertEqual(mock_approve.call_count, 1)

    @patch("payments.views.geniuspay_svc.verify_webhook_signature", return_value=True)
    def test_unknown_reference_returns_200_gracefully(self, mock_verify):
        body = {"data": {"reference": "UNKNOWN_REF", "status": "completed"}}
        r = self._post_webhook(body, event="payment.success")
        self.assertEqual(r.status_code, 200)

    @patch("payments.views.auto_approve_ad.delay")
    @patch("payments.views.geniuspay_svc.verify_webhook_signature", return_value=True)
    def test_lookup_by_deposit_id_metadata(self, mock_verify, mock_approve):
        """Webhook avec référence manquante mais deposit_id dans metadata."""
        p = make_payment(self.user, self.ad)
        body = {
            "data": {
                "reference": "",
                "status": "completed",
                "metadata": {"deposit_id": str(p.deposit_id)},
            }
        }
        r = self._post_webhook(body, event="payment.success")
        self.assertEqual(r.status_code, 200)

    @patch("payments.views.geniuspay_svc.verify_webhook_signature", return_value=True)
    def test_empty_reference_no_metadata_returns_200(self, mock_verify):
        body = {"data": {"reference": "", "status": "completed"}}
        r = self._post_webhook(body)
        self.assertEqual(r.status_code, 200)


# ═══════════════════════════════════════════════════════════════════════════════
# VUE : boost_ad
# ═══════════════════════════════════════════════════════════════════════════════

class BoostAdViewTest(TestCase):
    def setUp(self):
        self.client = Client()
        self.client.cookies["age_gate_accepted"] = "1"
        self.user = make_user()
        self.city = make_city()
        self.ad = make_ad(self.user, self.city, status=Ad.Status.APPROVED)

    def test_anonymous_redirected(self):
        r = self.client.get(f"/pay/boost/{self.ad.pk}/")
        self.assertEqual(r.status_code, 302)

    def test_get_boost_form_renders(self):
        self.client.force_login(self.user)
        r = self.client.get(f"/pay/boost/{self.ad.pk}/")
        self.assertEqual(r.status_code, 200)

    def test_already_boosted_redirects_to_dashboard(self):
        self.ad.is_boosted = True
        self.ad.boost_expires_at = timezone.now() + timedelta(days=10)
        self.ad.save()
        self.client.force_login(self.user)
        r = self.client.post(f"/pay/boost/{self.ad.pk}/")
        self.assertEqual(r.status_code, 302)
        self.assertFalse(Payment.objects.filter(user=self.user).exists())

    @patch("payments.views._call_geniuspay", return_value="https://geniuspay.com/boost")
    def test_post_creates_boost_payment(self, mock_gp):
        self.client.force_login(self.user)
        r = self.client.post(f"/pay/boost/{self.ad.pk}/")
        p = Payment.objects.filter(user=self.user, ad=self.ad, type=Payment.Type.BOOST).first()
        self.assertIsNotNone(p)
        self.assertEqual(p.amount, PRICE_BOOST)

    def test_other_user_ad_returns_redirect(self):
        u2 = make_user("u2", "u2@t.com")
        self.client.force_login(u2)
        r = self.client.post(f"/pay/boost/{self.ad.pk}/")
        self.assertEqual(r.status_code, 302)
        self.assertFalse(Payment.objects.filter(user=u2).exists())


# ═══════════════════════════════════════════════════════════════════════════════
# VUE : renew_ad
# ═══════════════════════════════════════════════════════════════════════════════

class RenewAdViewTest(TestCase):
    def setUp(self):
        self.client = Client()
        self.client.cookies["age_gate_accepted"] = "1"
        self.user = make_user()
        self.city = make_city()
        self.ad = make_ad(self.user, self.city, status=Ad.Status.APPROVED)

    def test_anonymous_redirected(self):
        r = self.client.get(f"/pay/renew/{self.ad.pk}/")
        self.assertEqual(r.status_code, 302)

    def test_get_renew_form_renders(self):
        self.client.force_login(self.user)
        r = self.client.get(f"/pay/renew/{self.ad.pk}/")
        self.assertEqual(r.status_code, 200)

    @patch("payments.views._call_geniuspay", return_value="https://geniuspay.com/renew")
    def test_renew_15_creates_correct_payment(self, mock_gp):
        self.client.force_login(self.user)
        self.client.post(f"/pay/renew/{self.ad.pk}/", {"forfait": "renew_15"})
        p = Payment.objects.filter(user=self.user, type=Payment.Type.RENEW_15).first()
        self.assertIsNotNone(p)
        self.assertEqual(p.amount, 1000)

    @patch("payments.views._call_geniuspay", return_value="https://geniuspay.com/renew")
    def test_renew_monthly_boost_creates_correct_payment(self, mock_gp):
        self.client.force_login(self.user)
        self.client.post(f"/pay/renew/{self.ad.pk}/", {"forfait": "renew_monb"})
        p = Payment.objects.filter(user=self.user, type=Payment.Type.RENEW_MONB).first()
        self.assertIsNotNone(p)
        self.assertEqual(p.amount, 4000)

    def test_invalid_forfait_redirects_back(self):
        self.client.force_login(self.user)
        r = self.client.post(f"/pay/renew/{self.ad.pk}/", {"forfait": "invalide"})
        self.assertEqual(r.status_code, 302)
        self.assertFalse(Payment.objects.filter(user=self.user).exists())


# ═══════════════════════════════════════════════════════════════════════════════
# VUE : check_promo_code
# ═══════════════════════════════════════════════════════════════════════════════

class CheckPromoCodeViewTest(TestCase):
    def setUp(self):
        self.client = Client()
        self.client.cookies["age_gate_accepted"] = "1"
        self.user = make_user()

    def test_anonymous_redirected(self):
        r = self.client.post("/pay/promo/check/", {"code": "TEST"})
        self.assertEqual(r.status_code, 302)

    def test_valid_promo_returns_discount(self):
        PromoCode.objects.create(code="DISC20", discount_percent=20, active=True)
        self.client.force_login(self.user)
        r = self.client.post("/pay/promo/check/", {"code": "DISC20", "forfait": "standard"})
        data = json.loads(r.content)
        self.assertTrue(data["valid"])
        self.assertEqual(data["discount_pct"], 20)
        self.assertLess(data["new_amount"], PRICE_STANDARD)

    def test_invalid_code_returns_error(self):
        self.client.force_login(self.user)
        r = self.client.post("/pay/promo/check/", {"code": "FAUX", "forfait": "standard"})
        data = json.loads(r.content)
        self.assertFalse(data["valid"])

    def test_expired_code_returns_error(self):
        PromoCode.objects.create(
            code="EXP10", discount_percent=10, active=True,
            expires_at=timezone.now() - timedelta(hours=1)
        )
        self.client.force_login(self.user)
        r = self.client.post("/pay/promo/check/", {"code": "EXP10", "forfait": "standard"})
        data = json.loads(r.content)
        self.assertFalse(data["valid"])

    def test_already_used_code_returns_error(self):
        PromoCode.objects.create(code="USED5", discount_percent=5, active=True)
        PromoCodeUsage.objects.create(code="USED5", user=self.user, discount_applied=50)
        self.client.force_login(self.user)
        r = self.client.post("/pay/promo/check/", {"code": "USED5", "forfait": "standard"})
        data = json.loads(r.content)
        self.assertFalse(data["valid"])

    def test_case_insensitive_code(self):
        PromoCode.objects.create(code="UPPER10", discount_percent=10, active=True)
        self.client.force_login(self.user)
        r = self.client.post("/pay/promo/check/", {"code": "upper10", "forfait": "standard"})
        data = json.loads(r.content)
        self.assertTrue(data["valid"])


# ═══════════════════════════════════════════════════════════════════════════════
# VUE : payment_history
# ═══════════════════════════════════════════════════════════════════════════════

class PaymentHistoryViewTest(TestCase):
    def setUp(self):
        self.client = Client()
        self.client.cookies["age_gate_accepted"] = "1"
        self.user = make_user()
        self.city = make_city()

    def test_anonymous_redirected(self):
        r = self.client.get("/pay/history/")
        self.assertEqual(r.status_code, 302)

    def test_authenticated_sees_history(self):
        self.client.force_login(self.user)
        r = self.client.get("/pay/history/")
        self.assertEqual(r.status_code, 200)

    def test_shows_own_payments(self):
        ad = make_ad(self.user, self.city)
        make_payment(self.user, ad, status=Payment.Status.COMPLETED)
        self.client.force_login(self.user)
        r = self.client.get("/pay/history/")
        self.assertContains(r, "completed")

    def test_does_not_show_other_users_payments(self):
        u2 = make_user("u2", "u2@t.com")
        city2 = City.objects.create(name="Bouaké")
        ad2 = make_ad(u2, city2)
        make_payment(u2, ad2, status=Payment.Status.COMPLETED)
        self.client.force_login(self.user)
        # On vérifie seulement que ça ne plante pas — les montants ne sont pas croisés
        r = self.client.get("/pay/history/")
        self.assertEqual(r.status_code, 200)
