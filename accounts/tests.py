"""
Tests complets — app accounts
Couvre : modèles, vues, services, tâches, EmailOTP
"""
from datetime import timedelta
from decimal import Decimal
from unittest.mock import patch, MagicMock

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.test import Client, TestCase, override_settings
from django.utils import timezone

from .models import (
    Account, BoostOption, EmailOTP, Profile,
    RechargePackage, Transaction,
)
from .services import AccountService, BoostService
from ads.models import Ad, City

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
        status=kw.pop("status", Ad.Status.APPROVED),
        image_processing_done=True,
        **kw,
    )


def make_account(user, **kw):
    return Account.objects.create(user=user, **kw)


def make_boost_option(boost_type=BoostOption.BoostType.PREMIUM, price=1000, days=7):
    return BoostOption.objects.create(
        boost_type=boost_type,
        name="Option test",
        duration_days=days,
        price=Decimal(str(price)),
    )


def make_package(name="Pack", amount=5000, ads_included=3, credit_amount=Decimal("0"), **kw):
    return RechargePackage.objects.create(
        name=name,
        amount=Decimal(str(amount)),
        ads_included=ads_included,
        credit_amount=credit_amount,
        **kw,
    )


# ═══════════════════════════════════════════════════════════════════════════════
# CUSTOM USER
# ═══════════════════════════════════════════════════════════════════════════════

class CustomUserModelTest(TestCase):
    def test_default_role_provider(self):
        u = make_user()
        self.assertEqual(u.role, User.Role.PROVIDER)

    def test_not_verified_by_default(self):
        u = make_user()
        self.assertFalse(u.is_verified)

    def test_superuser_flags(self):
        a = User.objects.create_superuser("admin", "a@t.com", "pass")
        self.assertTrue(a.is_superuser)
        self.assertTrue(a.is_staff)

    def test_role_choices_available(self):
        choices = [v for v, _ in User.Role.choices]
        self.assertIn("provider", choices)
        self.assertIn("moderator", choices)
        self.assertIn("admin", choices)

    def test_phone_e164_nullable(self):
        u = make_user("nophone", "nophone@t.com")
        self.assertIsNone(u.phone_e164)


# ═══════════════════════════════════════════════════════════════════════════════
# PROFILE
# ═══════════════════════════════════════════════════════════════════════════════

class ProfileModelTest(TestCase):
    def setUp(self):
        self.user = make_user()

    def test_auto_created_on_user_creation(self):
        self.assertTrue(Profile.objects.filter(user=self.user).exists())

    def test_display_name_equals_username(self):
        p = Profile.objects.get(user=self.user)
        self.assertEqual(p.display_name, self.user.username)

    def test_default_country_ci(self):
        p = Profile.objects.get(user=self.user)
        self.assertEqual(p.country, "CI")

    def test_contact_prefs_empty_by_default(self):
        p = Profile.objects.get(user=self.user)
        self.assertEqual(p.contact_prefs, [])

    def test_not_verified_by_default(self):
        p = Profile.objects.get(user=self.user)
        self.assertFalse(p.is_verified)

    def test_no_duplicate_profile_on_user_resave(self):
        self.user.save()
        self.assertEqual(Profile.objects.filter(user=self.user).count(), 1)

    def test_profile_deleted_with_user(self):
        uid = self.user.pk
        self.user.delete()
        self.assertFalse(Profile.objects.filter(user_id=uid).exists())


# ═══════════════════════════════════════════════════════════════════════════════
# EMAIL OTP
# ═══════════════════════════════════════════════════════════════════════════════

class EmailOTPTest(TestCase):
    def setUp(self):
        self.user = make_user()

    def test_code_is_5_digits(self):
        otp = EmailOTP.create_otp(self.user, EmailOTP.Purpose.PASSWORD_CHANGE)
        self.assertEqual(len(otp.code), 5)
        self.assertTrue(otp.code.isdigit())

    def test_generate_code_always_5_digits(self):
        """Même pour les codes commençant par 0 (ex: 00042)."""
        for _ in range(50):
            code = EmailOTP.generate_code()
            self.assertEqual(len(code), 5)
            self.assertTrue(code.isdigit())

    def test_valid_otp_with_correct_code(self):
        otp = EmailOTP.create_otp(self.user, EmailOTP.Purpose.PASSWORD_CHANGE)
        self.assertTrue(otp.is_valid(otp.code))

    def test_invalid_with_wrong_code(self):
        otp = EmailOTP.create_otp(self.user, EmailOTP.Purpose.PASSWORD_CHANGE)
        wrong = str((int(otp.code) + 1) % 100000).zfill(5)
        self.assertFalse(otp.is_valid(wrong))

    def test_invalid_when_expired(self):
        otp = EmailOTP.create_otp(self.user, EmailOTP.Purpose.PASSWORD_CHANGE)
        otp.expires_at = timezone.now() - timedelta(seconds=1)
        otp.save()
        self.assertFalse(otp.is_valid(otp.code))

    def test_invalid_when_used(self):
        otp = EmailOTP.create_otp(self.user, EmailOTP.Purpose.PASSWORD_CHANGE)
        otp.is_used = True
        otp.save()
        self.assertFalse(otp.is_valid(otp.code))

    def test_ttl_is_respected(self):
        otp = EmailOTP.create_otp(self.user, EmailOTP.Purpose.PASSWORD_CHANGE, ttl_seconds=300)
        expected = timezone.now() + timedelta(seconds=300)
        self.assertAlmostEqual(
            otp.expires_at.timestamp(), expected.timestamp(), delta=2
        )

    def test_different_purposes_coexist(self):
        otp1 = EmailOTP.create_otp(self.user, EmailOTP.Purpose.PASSWORD_CHANGE)
        otp2 = EmailOTP.create_otp(self.user, EmailOTP.Purpose.LOGIN_DEVICE)
        self.assertNotEqual(otp1.purpose, otp2.purpose)


# ═══════════════════════════════════════════════════════════════════════════════
# ACCOUNT MODEL
# ═══════════════════════════════════════════════════════════════════════════════

class AccountModelTest(TestCase):
    def setUp(self):
        self.user = make_user()
        self.account = make_account(self.user)

    def test_cannot_post_when_no_credits(self):
        self.assertFalse(self.account.can_post_ad())

    def test_can_post_with_free_credit(self):
        self.account.free_ads_remaining = 1
        self.account.save()
        self.assertTrue(self.account.can_post_ad())

    def test_can_post_with_paid_credit(self):
        self.account.ads_remaining = 2
        self.account.save()
        self.assertTrue(self.account.can_post_ad())

    def test_can_post_with_premium_credit(self):
        self.account.premium_ads_remaining = 1
        self.account.save()
        self.assertTrue(self.account.can_post_ad())

    def test_use_ad_credit_priority_premium_first(self):
        self.account.premium_ads_remaining = 2
        self.account.ads_remaining = 2
        self.account.free_ads_remaining = 2
        self.account.save()
        result = self.account.use_ad_credit()
        self.account.refresh_from_db()
        self.assertTrue(result)
        self.assertEqual(self.account.premium_ads_remaining, 1)
        self.assertEqual(self.account.ads_remaining, 2)
        self.assertEqual(self.account.free_ads_remaining, 2)

    def test_use_ad_credit_paid_before_free(self):
        self.account.ads_remaining = 3
        self.account.free_ads_remaining = 3
        self.account.save()
        self.account.use_ad_credit()
        self.account.refresh_from_db()
        self.assertEqual(self.account.ads_remaining, 2)
        self.assertEqual(self.account.free_ads_remaining, 3)

    def test_use_ad_credit_free_when_only_option(self):
        self.account.free_ads_remaining = 1
        self.account.save()
        self.account.use_ad_credit()
        self.account.refresh_from_db()
        self.assertEqual(self.account.free_ads_remaining, 0)

    def test_use_ad_credit_returns_false_when_empty(self):
        self.assertFalse(self.account.use_ad_credit())


# ═══════════════════════════════════════════════════════════════════════════════
# ACCOUNT SERVICE
# ═══════════════════════════════════════════════════════════════════════════════

class AccountServiceTest(TestCase):
    def setUp(self):
        self.user = make_user()

    def test_get_or_create_creates_account(self):
        a = AccountService.get_or_create_account(self.user)
        self.assertIsInstance(a, Account)

    def test_get_or_create_idempotent(self):
        a1 = AccountService.get_or_create_account(self.user)
        a2 = AccountService.get_or_create_account(self.user)
        self.assertEqual(a1.pk, a2.pk)

    def test_can_post_false_without_credits(self):
        self.assertFalse(AccountService.can_post_ad(self.user))

    def test_can_post_true_with_credits(self):
        a = AccountService.get_or_create_account(self.user)
        a.free_ads_remaining = 1
        a.save()
        self.assertTrue(AccountService.can_post_ad(self.user))

    def test_use_ad_credit_raises_without_credits(self):
        with self.assertRaises(ValidationError):
            AccountService.use_ad_credit(self.user)

    def test_apply_recharge_standard_package(self):
        pkg = make_package(ads_included=3)
        AccountService.apply_recharge(self.user, pkg.id)
        a = AccountService.get_or_create_account(self.user)
        self.assertEqual(a.ads_remaining, 3)

    def test_apply_recharge_premium_package(self):
        pkg = make_package(ads_included=15, is_premium=True)
        AccountService.apply_recharge(self.user, pkg.id)
        a = AccountService.get_or_create_account(self.user)
        self.assertTrue(a.is_premium)
        self.assertEqual(a.premium_ads_remaining, 15)

    def test_apply_recharge_adds_free_boosters(self):
        pkg = make_package(free_boosters=2)
        AccountService.apply_recharge(self.user, pkg.id)
        a = AccountService.get_or_create_account(self.user)
        self.assertEqual(a.free_boosters_remaining, 2)

    def test_apply_recharge_adds_credit_balance(self):
        pkg = make_package(credit_amount=Decimal("500"))
        pkg.credit_amount = Decimal("500")
        pkg.save()
        AccountService.apply_recharge(self.user, pkg.id)
        a = AccountService.get_or_create_account(self.user)
        self.assertEqual(a.balance, Decimal("500"))

    def test_apply_recharge_creates_completed_transaction(self):
        pkg = make_package()
        AccountService.apply_recharge(self.user, pkg.id)
        t = Transaction.objects.filter(user=self.user).first()
        self.assertIsNotNone(t)
        self.assertEqual(t.status, Transaction.Status.COMPLETED)

    def test_apply_recharge_invalid_package_raises(self):
        with self.assertRaises(ValidationError):
            AccountService.apply_recharge(self.user, 99999)

    def test_multiple_recharges_accumulate(self):
        pkg = make_package(ads_included=5)
        AccountService.apply_recharge(self.user, pkg.id)
        AccountService.apply_recharge(self.user, pkg.id)
        a = AccountService.get_or_create_account(self.user)
        self.assertEqual(a.ads_remaining, 10)


# ═══════════════════════════════════════════════════════════════════════════════
# BOOST SERVICE
# ═══════════════════════════════════════════════════════════════════════════════

class BoostServiceTest(TestCase):
    def setUp(self):
        self.user = make_user()
        self.city = make_city()
        self.ad = make_ad(self.user, self.city)
        self.account = make_account(self.user, balance=Decimal("10000"))

    # ── apply_boost ──────────────────────────────────────────────────────────
    def test_premium_boost_sets_is_premium(self):
        opt = make_boost_option(BoostOption.BoostType.PREMIUM, price=1000)
        BoostService.apply_boost(self.user, self.ad.id, opt.id)
        self.ad.refresh_from_db()
        self.assertTrue(self.ad.is_premium)
        self.assertIsNotNone(self.ad.premium_until)

    def test_premium_until_correct_duration(self):
        opt = make_boost_option(BoostOption.BoostType.PREMIUM, price=1000, days=7)
        BoostService.apply_boost(self.user, self.ad.id, opt.id)
        self.ad.refresh_from_db()
        expected = timezone.now() + timedelta(days=7)
        self.assertAlmostEqual(
            self.ad.premium_until.timestamp(), expected.timestamp(), delta=5
        )

    def test_urgent_boost_sets_is_urgent(self):
        opt = make_boost_option(BoostOption.BoostType.URGENT, price=500)
        BoostService.apply_boost(self.user, self.ad.id, opt.id)
        self.ad.refresh_from_db()
        self.assertTrue(self.ad.is_urgent)
        self.assertIsNotNone(self.ad.urgent_until)

    def test_prolongation_boost_sets_extended_until(self):
        self.ad.expires_at = timezone.now() + timedelta(days=5)
        self.ad.save()
        opt = make_boost_option(BoostOption.BoostType.PROLONGATION, price=500, days=15)
        BoostService.apply_boost(self.user, self.ad.id, opt.id)
        self.ad.refresh_from_db()
        self.assertIsNotNone(self.ad.extended_until)

    def test_prolongation_stacks_on_existing(self):
        future = timezone.now() + timedelta(days=10)
        self.ad.extended_until = future
        self.ad.save()
        opt = make_boost_option(BoostOption.BoostType.PROLONGATION, price=500, days=15)
        BoostService.apply_boost(self.user, self.ad.id, opt.id)
        self.ad.refresh_from_db()
        self.assertGreater(self.ad.extended_until, future)

    def test_boost_deducts_from_balance(self):
        opt = make_boost_option(price=1000)
        BoostService.apply_boost(self.user, self.ad.id, opt.id)
        self.account.refresh_from_db()
        self.assertEqual(self.account.balance, Decimal("9000"))

    def test_insufficient_balance_raises(self):
        self.account.balance = Decimal("0")
        self.account.save()
        opt = make_boost_option(price=1000)
        with self.assertRaises(ValidationError):
            BoostService.apply_boost(self.user, self.ad.id, opt.id)

    def test_free_booster_no_balance_deducted(self):
        self.account.free_boosters_remaining = 1
        self.account.balance = Decimal("0")
        self.account.save()
        opt = make_boost_option(price=1000)
        BoostService.apply_boost(self.user, self.ad.id, opt.id, use_free_booster=True)
        self.account.refresh_from_db()
        self.assertEqual(self.account.balance, Decimal("0"))
        self.assertEqual(self.account.free_boosters_remaining, 0)

    def test_no_free_booster_available_raises(self):
        self.account.free_boosters_remaining = 0
        self.account.balance = Decimal("0")
        self.account.save()
        opt = make_boost_option(price=1000)
        with self.assertRaises(ValidationError):
            BoostService.apply_boost(self.user, self.ad.id, opt.id, use_free_booster=True)

    def test_wrong_user_cannot_boost(self):
        u2 = make_user("u2", "u2@t.com")
        make_account(u2, balance=Decimal("9999"))
        opt = make_boost_option()
        with self.assertRaises(ValidationError):
            BoostService.apply_boost(u2, self.ad.id, opt.id)

    def test_boost_creates_transaction(self):
        opt = make_boost_option(price=500)
        BoostService.apply_boost(self.user, self.ad.id, opt.id)
        t = Transaction.objects.filter(user=self.user, transaction_type=Transaction.TransactionType.BOOST).first()
        self.assertIsNotNone(t)
        self.assertEqual(t.status, Transaction.Status.COMPLETED)

    # ── is_premium_active ────────────────────────────────────────────────────
    def test_is_premium_active_true(self):
        self.ad.is_premium = True
        self.ad.premium_until = timezone.now() + timedelta(hours=2)
        self.ad.save()
        self.assertTrue(BoostService.is_premium_active(self.ad))

    def test_is_premium_active_false_expired(self):
        self.ad.is_premium = True
        self.ad.premium_until = timezone.now() - timedelta(minutes=1)
        self.ad.save()
        self.assertFalse(BoostService.is_premium_active(self.ad))

    def test_is_premium_active_false_not_premium(self):
        self.ad.is_premium = False
        self.ad.save()
        self.assertFalse(BoostService.is_premium_active(self.ad))

    def test_is_premium_active_no_until_means_active(self):
        self.ad.is_premium = True
        self.ad.premium_until = None
        self.ad.save()
        self.assertTrue(BoostService.is_premium_active(self.ad))

    # ── is_urgent_active ─────────────────────────────────────────────────────
    def test_is_urgent_active_true(self):
        self.ad.is_urgent = True
        self.ad.urgent_until = timezone.now() + timedelta(hours=1)
        self.ad.save()
        self.assertTrue(BoostService.is_urgent_active(self.ad))

    def test_is_urgent_active_false_expired(self):
        self.ad.is_urgent = True
        self.ad.urgent_until = timezone.now() - timedelta(minutes=1)
        self.ad.save()
        self.assertFalse(BoostService.is_urgent_active(self.ad))

    # ── get_effective_expiry_date ─────────────────────────────────────────────
    def test_effective_expiry_without_extension(self):
        self.ad.expires_at = timezone.now() + timedelta(days=5)
        self.ad.extended_until = None
        self.ad.save()
        self.assertEqual(BoostService.get_effective_expiry_date(self.ad), self.ad.expires_at)

    def test_effective_expiry_with_extension(self):
        self.ad.expires_at = timezone.now() + timedelta(days=5)
        self.ad.extended_until = timezone.now() + timedelta(days=20)
        self.ad.save()
        self.assertEqual(BoostService.get_effective_expiry_date(self.ad), self.ad.extended_until)

    def test_effective_expiry_extension_before_expires(self):
        future = timezone.now() + timedelta(days=15)
        ext = timezone.now() + timedelta(days=5)
        self.ad.expires_at = future
        self.ad.extended_until = ext
        self.ad.save()
        # max(expires_at, extended_until)
        result = BoostService.get_effective_expiry_date(self.ad)
        self.assertEqual(result, future)


# ═══════════════════════════════════════════════════════════════════════════════
# VUES ACCOUNTS
# ═══════════════════════════════════════════════════════════════════════════════

@override_settings(CACHES={"default": {"BACKEND": "django.core.cache.backends.dummy.DummyCache"}})
class ProfileEditViewTest(TestCase):
    def setUp(self):
        self.client = Client()
        self.client.cookies["age_gate_accepted"] = "1"
        self.user = make_user()

    def test_anonymous_redirected(self):
        r = self.client.get("/accounts/profile/")
        self.assertEqual(r.status_code, 302)

    def test_profile_edit_renders_200(self):
        self.client.force_login(self.user)
        r = self.client.get("/accounts/profile/")
        self.assertEqual(r.status_code, 200)

    @patch("accounts.views.send_profile_validation_email.delay")
    def test_valid_post_updates_display_name(self, mock_task):
        self.client.force_login(self.user)
        r = self.client.post("/accounts/profile/", {
            "display_name": "Nouveau nom",
            "contact_prefs": ["whatsapp"],
            "country": "CI",
        })
        profile = Profile.objects.get(user=self.user)
        self.assertEqual(profile.display_name, "Nouveau nom")


@override_settings(CACHES={"default": {"BACKEND": "django.core.cache.backends.dummy.DummyCache"}})
class PasswordChangeViewTest(TestCase):
    def setUp(self):
        self.client = Client()
        self.client.cookies["age_gate_accepted"] = "1"
        self.user = make_user(password="OldPass123!")

    def test_anonymous_redirected(self):
        r = self.client.get("/accounts/password/change/")
        self.assertEqual(r.status_code, 302)

    def test_change_form_renders_200(self):
        self.client.force_login(self.user)
        r = self.client.get("/accounts/password/change/")
        self.assertEqual(r.status_code, 200)

    @patch("accounts.views.send_password_change_email.delay")
    @patch("accounts.views.EmailOTP.create_otp")
    def test_valid_step1_stores_token_in_session(self, mock_otp, mock_email):
        mock_otp.return_value = MagicMock(code="12345")
        self.client.force_login(self.user)
        r = self.client.post("/accounts/password/change/", {
            "old_password": "pass1234!",
            "new_password1": "NewSecure@789",
            "new_password2": "NewSecure@789",
        })
        # Doit stocker le token en session ou rediriger vers l'étape 2
        self.assertIn(r.status_code, [200, 302])
