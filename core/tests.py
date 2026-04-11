"""
Tests complets — app core
Couvre : landing, age_gate, post, edit_ad, delete_ad, dashboard,
         health_check, report_ad, legal pages, rate limiting
"""
import json
from io import BytesIO
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import Client, TestCase, override_settings
from django.utils import timezone

from ads.models import Ad, AdMedia, City, Report
from accounts.models import Profile

User = get_user_model()


# ─── Factories ────────────────────────────────────────────────────────────────

def make_user(username="u1", email="u1@test.com", password="pass1234!"):
    return User.objects.create_user(username=username, email=email, password=password)


def make_city(name="Abidjan"):
    return City.objects.create(name=name, region="Lagunes")


def make_ad(user, city, **kw):
    return Ad.objects.create(
        user=user,
        title=kw.pop("title", "Annonce test"),
        description_sanitized=kw.pop("description_sanitized", "Description"),
        category=kw.pop("category", Ad.Category.ESCORTE_GIRL),
        city=city,
        status=kw.pop("status", Ad.Status.APPROVED),
        image_processing_done=True,
        **kw,
    )


def jpeg_file(name="photo.jpg", size=1024):
    """JPEG minimal valide (magic bytes JFIF)."""
    content = b"\xff\xd8\xff\xe0\x00\x10JFIF\x00\x01" + b"\x00" * size + b"\xff\xd9"
    return SimpleUploadedFile(name, content, content_type="image/jpeg")


def post_data(city, **kw):
    """Données POST minimales valides pour le formulaire d'annonce."""
    return {
        "title": kw.get("title", "Belle annonce test"),
        "category": kw.get("category", "escorte_girl"),
        "subcategories": kw.get("subcategories", []),
        "description": kw.get("description", "Description valide de l'annonce."),
        "city": str(city.pk),
        "phone1": kw.get("phone1", "+22507000001"),
        "phone2": kw.get("phone2", ""),
        "contact_methods": kw.get("contact_methods", ["whatsapp"]),
    }


# ═══════════════════════════════════════════════════════════════════════════════
# AGE GATE
# ═══════════════════════════════════════════════════════════════════════════════

class AgeGateTest(TestCase):
    def setUp(self):
        self.client = Client()

    def test_redirect_to_age_gate_without_cookie(self):
        r = self.client.get("/")
        self.assertRedirects(r, "/age-gate/", fetch_redirect_response=False)

    def test_access_root_with_cookie(self):
        self.client.cookies["age_gate_accepted"] = "1"
        r = self.client.get("/")
        self.assertIn(r.status_code, [200, 301, 302])

    def test_age_gate_page_renders(self):
        r = self.client.get("/age-gate/")
        self.assertEqual(r.status_code, 200)

    def test_post_sets_cookie_and_redirects(self):
        r = self.client.post("/age-gate/")
        self.assertRedirects(r, "/", fetch_redirect_response=False)
        self.assertEqual(self.client.cookies["age_gate_accepted"].value, "1")

    def test_connected_user_exempt_from_age_gate(self):
        u = make_user()
        self.client.force_login(u)
        r = self.client.get("/ads/")
        self.assertNotEqual(r.status_code, 302)


# ═══════════════════════════════════════════════════════════════════════════════
# LANDING + HEALTH
# ═══════════════════════════════════════════════════════════════════════════════

class LandingAndHealthTest(TestCase):
    def setUp(self):
        self.client = Client()
        self.client.cookies["age_gate_accepted"] = "1"

    def test_landing_redirects_301(self):
        r = self.client.get("/")
        self.assertIn(r.status_code, [301, 302])

    def test_health_check_200_with_db(self):
        r = self.client.get("/health/")
        self.assertEqual(r.status_code, 200)
        data = json.loads(r.content)
        self.assertEqual(data["status"], "ok")
        self.assertTrue(data["db"])

    def test_health_check_json_content_type(self):
        r = self.client.get("/health/")
        self.assertIn("application/json", r["Content-Type"])


# ═══════════════════════════════════════════════════════════════════════════════
# PAGE LÉGALES
# ═══════════════════════════════════════════════════════════════════════════════

class LegalPagesTest(TestCase):
    def setUp(self):
        self.client = Client()
        self.client.cookies["age_gate_accepted"] = "1"

    def test_tos_200(self):
        r = self.client.get("/legal/tos/")
        self.assertEqual(r.status_code, 200)

    def test_privacy_200(self):
        r = self.client.get("/legal/privacy/")
        self.assertEqual(r.status_code, 200)

    def test_content_policy_200(self):
        r = self.client.get("/legal/content-policy/")
        self.assertEqual(r.status_code, 200)


# ═══════════════════════════════════════════════════════════════════════════════
# DASHBOARD
# ═══════════════════════════════════════════════════════════════════════════════

class DashboardTest(TestCase):
    def setUp(self):
        self.client = Client()
        self.client.cookies["age_gate_accepted"] = "1"
        self.user = make_user()
        self.city = make_city()

    def test_anonymous_redirected_to_login(self):
        r = self.client.get("/dashboard/")
        self.assertEqual(r.status_code, 302)
        self.assertIn("login", r["Location"])

    def test_authenticated_user_sees_dashboard(self):
        self.client.force_login(self.user)
        r = self.client.get("/dashboard/")
        self.assertEqual(r.status_code, 200)

    def test_dashboard_shows_own_ads(self):
        self.client.force_login(self.user)
        make_ad(self.user, self.city, title="Mon annonce perso")
        r = self.client.get("/dashboard/")
        self.assertContains(r, "Mon annonce perso")

    def test_dashboard_does_not_show_other_users_ads(self):
        u2 = make_user("u2", "u2@t.com")
        make_ad(u2, self.city, title="Annonce autre user")
        self.client.force_login(self.user)
        r = self.client.get("/dashboard/")
        self.assertNotContains(r, "Annonce autre user")

    def test_dashboard_shows_all_statuses(self):
        """Le dashboard montre les annonces peu importe leur statut."""
        self.client.force_login(self.user)
        make_ad(self.user, self.city, title="Draft", status=Ad.Status.DRAFT)
        make_ad(self.user, self.city, title="Approved", status=Ad.Status.APPROVED)
        make_ad(self.user, self.city, title="Expired", status=Ad.Status.EXPIRED)
        r = self.client.get("/dashboard/")
        self.assertContains(r, "Draft")
        self.assertContains(r, "Approved")
        self.assertContains(r, "Expired")

    def test_dashboard_pagination(self):
        self.client.force_login(self.user)
        for i in range(22):
            make_ad(self.user, self.city, title=f"Ad {i}")
        r = self.client.get("/dashboard/?page=2")
        self.assertEqual(r.status_code, 200)


# ═══════════════════════════════════════════════════════════════════════════════
# VUE : post (création d'annonce)
# ═══════════════════════════════════════════════════════════════════════════════

@override_settings(
    USE_ASYNC_IMAGE_PROCESSING=False,
    CACHES={"default": {"BACKEND": "django.core.cache.backends.dummy.DummyCache"}},
)
class PostAdViewTest(TestCase):
    def setUp(self):
        self.client = Client()
        self.client.cookies["age_gate_accepted"] = "1"
        self.user = make_user()
        self.city = make_city()
        self.client.force_login(self.user)

    def _post(self, extra_files=None, **kw):
        data = post_data(self.city, **kw)
        files = {"images": [jpeg_file()]}
        if extra_files:
            files.update(extra_files)
        return self.client.post("/post/", data={**data, **files})

    def test_anonymous_redirected_to_login(self):
        self.client.logout()
        r = self.client.post("/post/", {})
        self.assertEqual(r.status_code, 302)

    def test_get_post_form_renders(self):
        r = self.client.get("/post/")
        self.assertEqual(r.status_code, 200)

    def test_valid_post_creates_draft_ad(self):
        r = self._post()
        self.assertEqual(Ad.objects.filter(user=self.user, status=Ad.Status.DRAFT).count(), 1)

    def test_valid_post_redirects_to_payment(self):
        r = self._post()
        self.assertEqual(r.status_code, 302)
        self.assertIn("pay", r["Location"])

    def test_valid_post_stores_ad_id_in_session(self):
        self._post()
        self.assertIn("pending_ad_id", self.client.session)

    def test_post_without_image_shows_error(self):
        data = post_data(self.city)
        r = self.client.post("/post/", data)
        self.assertEqual(r.status_code, 200)
        self.assertContains(r, "photo")

    def test_post_with_invalid_category_fails(self):
        data = post_data(self.city, category="invalid_cat")
        data["images"] = jpeg_file()
        r = self.client.post("/post/", data)
        self.assertEqual(r.status_code, 200)
        self.assertEqual(Ad.objects.filter(user=self.user).count(), 0)

    def test_rate_limit_3_ads_per_hour(self):
        """La 4e annonce dans la même heure est bloquée."""
        for _ in range(3):
            Ad.objects.create(
                user=self.user, title="Spam", description_sanitized="D",
                category=Ad.Category.ESCORTE_GIRL, city=self.city,
                created_at=timezone.now(),
            )
        r = self._post(title="4e annonce")
        self.assertContains(r, "Limite")

    def test_phone_used_by_other_account_blocked(self):
        u2 = make_user("u2", "u2@t.com")
        u2.phone_e164 = "+22507000001"
        u2.save()
        data = post_data(self.city, phone1="+22507000001")
        data["images"] = jpeg_file()
        r = self.client.post("/post/", data)
        self.assertContains(r, "déjà utilisé")


# ═══════════════════════════════════════════════════════════════════════════════
# VUE : delete_ad
# ═══════════════════════════════════════════════════════════════════════════════

@override_settings(CACHES={"default": {"BACKEND": "django.core.cache.backends.dummy.DummyCache"}})
class DeleteAdViewTest(TestCase):
    def setUp(self):
        self.client = Client()
        self.client.cookies["age_gate_accepted"] = "1"
        self.user = make_user()
        self.city = make_city()

    @patch("core.views.EmailService.send_email")
    def test_owner_can_delete_ad(self, mock_email):
        ad = make_ad(self.user, self.city)
        self.client.force_login(self.user)
        r = self.client.post(f"/delete/{ad.pk}/")
        self.assertEqual(r.status_code, 200)
        data = json.loads(r.content)
        self.assertTrue(data["ok"])
        self.assertFalse(Ad.objects.filter(pk=ad.pk).exists())

    @patch("core.views.EmailService.send_email")
    def test_delete_sends_email(self, mock_email):
        ad = make_ad(self.user, self.city)
        self.client.force_login(self.user)
        self.client.post(f"/delete/{ad.pk}/")
        mock_email.assert_called_once()

    def test_anonymous_cannot_delete(self):
        ad = make_ad(self.user, self.city)
        r = self.client.post(f"/delete/{ad.pk}/")
        self.assertEqual(r.status_code, 302)
        self.assertTrue(Ad.objects.filter(pk=ad.pk).exists())

    def test_other_user_cannot_delete(self):
        u2 = make_user("u2", "u2@t.com")
        ad = make_ad(self.user, self.city)
        self.client.force_login(u2)
        r = self.client.post(f"/delete/{ad.pk}/")
        self.assertEqual(r.status_code, 404)
        self.assertTrue(Ad.objects.filter(pk=ad.pk).exists())

    def test_get_method_not_allowed(self):
        ad = make_ad(self.user, self.city)
        self.client.force_login(self.user)
        r = self.client.get(f"/delete/{ad.pk}/")
        self.assertEqual(r.status_code, 405)


# ═══════════════════════════════════════════════════════════════════════════════
# VUE : edit_ad
# ═══════════════════════════════════════════════════════════════════════════════

@override_settings(
    USE_ASYNC_IMAGE_PROCESSING=False,
    CACHES={"default": {"BACKEND": "django.core.cache.backends.dummy.DummyCache"}},
)
class EditAdViewTest(TestCase):
    def setUp(self):
        self.client = Client()
        self.client.cookies["age_gate_accepted"] = "1"
        self.user = make_user()
        self.city = make_city()

    def test_owner_sees_edit_form(self):
        ad = make_ad(self.user, self.city)
        self.client.force_login(self.user)
        r = self.client.get(f"/edit/{ad.pk}/")
        self.assertEqual(r.status_code, 200)

    def test_other_user_redirected(self):
        u2 = make_user("u2", "u2@t.com")
        ad = make_ad(self.user, self.city)
        self.client.force_login(u2)
        r = self.client.get(f"/edit/{ad.pk}/")
        self.assertEqual(r.status_code, 302)

    def test_anonymous_redirected_to_login(self):
        ad = make_ad(self.user, self.city)
        r = self.client.get(f"/edit/{ad.pk}/")
        self.assertEqual(r.status_code, 302)

    def test_valid_edit_updates_title(self):
        ad = make_ad(self.user, self.city)
        self.client.force_login(self.user)
        data = post_data(self.city, title="Titre modifié")
        r = self.client.post(f"/edit/{ad.pk}/", data)
        ad.refresh_from_db()
        self.assertEqual(ad.title, "Titre modifié")
        self.assertRedirects(r, "/dashboard/", fetch_redirect_response=False)

    def test_valid_edit_updates_category(self):
        ad = make_ad(self.user, self.city)
        self.client.force_login(self.user)
        data = post_data(self.city, category="escorte_boy")
        self.client.post(f"/edit/{ad.pk}/", data)
        ad.refresh_from_db()
        self.assertEqual(ad.category, "escorte_boy")


# ═══════════════════════════════════════════════════════════════════════════════
# VUE : report_ad
# ═══════════════════════════════════════════════════════════════════════════════

@override_settings(CACHES={"default": {"BACKEND": "django.core.cache.backends.dummy.DummyCache"}})
class ReportAdTest(TestCase):
    def setUp(self):
        self.client = Client()
        self.client.cookies["age_gate_accepted"] = "1"
        self.user = make_user()
        self.city = make_city()
        self.ad = make_ad(self.user, self.city)

    def test_report_form_renders(self):
        r = self.client.get(f"/report/{self.ad.pk}/")
        self.assertEqual(r.status_code, 200)

    @patch("core.views.EmailService.send_email", return_value=None)
    def test_post_report_creates_report_object(self, mock_email):
        r = self.client.post(f"/report/{self.ad.pk}/", {
            "reason": "spam",
            "details": "Contenu inapproprié",
        })
        self.assertTrue(Report.objects.filter(ad=self.ad).exists())

    def test_report_unknown_ad_returns_404(self):
        r = self.client.get("/report/99999/")
        self.assertEqual(r.status_code, 404)


# ═══════════════════════════════════════════════════════════════════════════════
# VUE : public_profile (via accounts)
# ═══════════════════════════════════════════════════════════════════════════════

class PublicProfileTest(TestCase):
    def setUp(self):
        self.client = Client()
        self.client.cookies["age_gate_accepted"] = "1"
        self.user = make_user(username="johndoe")
        self.city = make_city()

    def test_public_profile_renders_200(self):
        r = self.client.get(f"/accounts/u/{self.user.username}/")
        self.assertEqual(r.status_code, 200)

    def test_public_profile_unknown_user_404(self):
        r = self.client.get("/accounts/u/utilisateur-inconnu/")
        self.assertEqual(r.status_code, 404)

    def test_public_profile_shows_approved_ads(self):
        make_ad(self.user, self.city, title="Annonce publique")
        r = self.client.get(f"/accounts/u/{self.user.username}/")
        self.assertContains(r, "Annonce publique")

    def test_public_profile_hides_draft_ads(self):
        make_ad(self.user, self.city, title="Mon brouillon", status=Ad.Status.DRAFT)
        r = self.client.get(f"/accounts/u/{self.user.username}/")
        self.assertNotContains(r, "Mon brouillon")


# ═══════════════════════════════════════════════════════════════════════════════
# 404 et handlers
# ═══════════════════════════════════════════════════════════════════════════════

class ErrorHandlersTest(TestCase):
    def setUp(self):
        self.client = Client()
        self.client.cookies["age_gate_accepted"] = "1"

    def test_404_on_unknown_url(self):
        r = self.client.get("/cette-url-nexiste-absolument-pas/")
        self.assertEqual(r.status_code, 404)
