"""
Tests complets — app ads
Couvre : modèles, vues, tâches Celery, formulaires
"""
import json
from datetime import timedelta
from io import BytesIO
from unittest.mock import MagicMock, patch

from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.core.exceptions import ValidationError
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import Client, TestCase, override_settings
from django.utils import timezone

from .models import Ad, AdMedia, City, Favorite, Report
from .tasks import (
    expire_ads,
    expire_premium_ads,
    notify_expiring_soon_1h,
    notify_expiring_soon_24h,
    promote_boosted_ads,
    purge_expired_ads,
)

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
        description_sanitized=kw.pop("description_sanitized", "Description test"),
        category=kw.pop("category", Ad.Category.ESCORTE_GIRL),
        city=city,
        status=kw.pop("status", Ad.Status.APPROVED),
        image_processing_done=kw.pop("image_processing_done", True),
        **kw,
    )


def jpeg_image(name="photo.jpg"):
    """Retourne un SimpleUploadedFile simulant un JPEG valide (magic bytes)."""
    content = (
        b"\xff\xd8\xff\xe0\x00\x10JFIF\x00\x01\x01\x00\x00\x01\x00\x01\x00\x00"
        + b"\xff\xd9"
    )
    return SimpleUploadedFile(name, content, content_type="image/jpeg")


# ═══════════════════════════════════════════════════════════════════════════════
# MODÈLES
# ═══════════════════════════════════════════════════════════════════════════════

class CityModelTest(TestCase):
    def test_slug_auto_generated(self):
        c = City.objects.create(name="Yamoussoukro")
        self.assertEqual(c.slug, "yamoussoukro")

    def test_slug_strips_accents(self):
        c = City.objects.create(name="San-Pédro")
        self.assertNotIn("é", c.slug)
        self.assertTrue(c.slug)

    def test_name_unique(self):
        City.objects.create(name="Bouaké")
        with self.assertRaises(Exception):
            City.objects.create(name="Bouaké")

    def test_str_is_name(self):
        c = City.objects.create(name="Abidjan")
        self.assertEqual(str(c), "Abidjan")


class AdModelTest(TestCase):
    def setUp(self):
        self.user = make_user()
        self.city = make_city()

    # ── Création / valeurs par défaut ────────────────────────────────────────
    def test_default_status_is_draft(self):
        ad = Ad.objects.create(
            user=self.user, title="T", description_sanitized="D",
            category=Ad.Category.ESCORTE_GIRL, city=self.city,
        )
        self.assertEqual(ad.status, Ad.Status.DRAFT)

    def test_contacts_clicks_initialized(self):
        ad = make_ad(self.user, self.city)
        self.assertEqual(ad.contacts_clicks, {"sms": 0, "whatsapp": 0, "call": 0})

    def test_expires_at_set_to_5_days(self):
        before = timezone.now()
        ad = make_ad(self.user, self.city)
        self.assertAlmostEqual(
            (ad.expires_at - before).total_seconds(),
            5 * 86400,
            delta=10,
        )

    def test_expires_at_preserved_when_set(self):
        custom = timezone.now() + timedelta(days=30)
        ad = make_ad(self.user, self.city, expires_at=custom)
        self.assertEqual(ad.expires_at, custom)

    # ── Slug ────────────────────────────────────────────────────────────────
    def test_slug_generated_from_title(self):
        ad = make_ad(self.user, self.city, title="Belle annonce Abidjan")
        self.assertEqual(ad.slug, "belle-annonce-abidjan")

    def test_duplicate_slug_incremented(self):
        a1 = make_ad(self.user, self.city, title="Test")
        a2 = make_ad(self.user, self.city, title="Test")
        self.assertNotEqual(a1.slug, a2.slug)
        self.assertTrue(a2.slug.endswith("-2"))

    def test_third_duplicate_incremented(self):
        make_ad(self.user, self.city, title="Dup")
        make_ad(self.user, self.city, title="Dup")
        a3 = make_ad(self.user, self.city, title="Dup")
        self.assertTrue(a3.slug.endswith("-3"))

    # ── Catégories / sous-catégories ─────────────────────────────────────────
    def test_all_categories_available(self):
        values = [v for v, _ in Ad.Category.choices]
        self.assertIn("escorte_girl", values)
        self.assertIn("escorte_boy", values)
        self.assertIn("transgenre", values)

    def test_valid_subcategory_passes(self):
        ad = Ad(
            user=self.user, title="T", description_sanitized="D",
            category=Ad.Category.ESCORTE_GIRL, city=self.city,
            subcategories=["Sex vaginal"],
        )
        ad.clean()  # doit passer sans exception

    def test_invalid_subcategory_raises(self):
        ad = Ad(
            user=self.user, title="T", description_sanitized="D",
            category=Ad.Category.ESCORTE_GIRL, city=self.city,
            subcategories=["inexistant"],
        )
        with self.assertRaises(ValidationError) as ctx:
            ad.clean()
        self.assertIn("subcategories", ctx.exception.message_dict)

    def test_multiple_valid_subcategories(self):
        ad = Ad(
            user=self.user, title="T", description_sanitized="D",
            category=Ad.Category.ESCORTE_GIRL, city=self.city,
            subcategories=["Sex vaginal", "Massage sexuel"],
        )
        ad.clean()

    def test_empty_subcategories_valid(self):
        ad = Ad(
            user=self.user, title="T", description_sanitized="D",
            category=Ad.Category.ESCORTE_GIRL, city=self.city,
            subcategories=[],
        )
        ad.clean()


class AdMediaModelTest(TestCase):
    def setUp(self):
        self.user = make_user()
        self.city = make_city()
        self.ad = make_ad(self.user, self.city)

    def test_max_5_photos_enforced(self):
        for i in range(5):
            AdMedia.objects.create(ad=self.ad, image=f"img{i}.jpg")
        with self.assertRaises(ValidationError):
            m = AdMedia(ad=self.ad, image="img6.jpg")
            m.clean()

    def test_4_photos_allowed(self):
        for i in range(4):
            AdMedia.objects.create(ad=self.ad, image=f"img{i}.jpg")
        # Ne doit pas lever
        m = AdMedia(ad=self.ad, image="img5.jpg")
        m.clean()

    def test_primary_flag_exclusive(self):
        m1 = AdMedia.objects.create(ad=self.ad, image="a.jpg", is_primary=True)
        m2 = AdMedia.objects.create(ad=self.ad, image="b.jpg", is_primary=True)
        m1.refresh_from_db()
        m2.refresh_from_db()
        self.assertFalse(m1.is_primary)
        self.assertTrue(m2.is_primary)

    def test_single_primary_stays_primary(self):
        m = AdMedia.objects.create(ad=self.ad, image="only.jpg", is_primary=True)
        m.refresh_from_db()
        self.assertTrue(m.is_primary)


# ═══════════════════════════════════════════════════════════════════════════════
# VUE : ad_list
# ═══════════════════════════════════════════════════════════════════════════════

@override_settings(CACHES={"default": {"BACKEND": "django.core.cache.backends.dummy.DummyCache"}})
class AdListViewTest(TestCase):
    def setUp(self):
        self.client = Client()
        self.client.cookies["age_gate_accepted"] = "1"
        self.user = make_user()
        self.city = make_city()

    def test_returns_200(self):
        r = self.client.get("/ads/")
        self.assertEqual(r.status_code, 200)

    def test_shows_approved_ad(self):
        make_ad(self.user, self.city, title="Visible")
        r = self.client.get("/ads/")
        self.assertContains(r, "Visible")

    def test_hides_draft(self):
        make_ad(self.user, self.city, title="Brouillon", status=Ad.Status.DRAFT)
        r = self.client.get("/ads/")
        self.assertNotContains(r, "Brouillon")

    def test_hides_rejected(self):
        make_ad(self.user, self.city, title="Rejetée", status=Ad.Status.REJECTED)
        r = self.client.get("/ads/")
        self.assertNotContains(r, "Rejetée")

    def test_shows_expired(self):
        make_ad(self.user, self.city, title="Expirée", status=Ad.Status.EXPIRED)
        r = self.client.get("/ads/")
        self.assertContains(r, "Expirée")

    def test_hides_image_not_processed(self):
        make_ad(self.user, self.city, title="SansFiligrane", image_processing_done=False)
        r = self.client.get("/ads/")
        self.assertNotContains(r, "SansFiligrane")

    def test_filter_by_city(self):
        city2 = make_city("Bouaké")
        make_ad(self.user, self.city, title="Abidjan Ad")
        make_ad(self.user, city2, title="Bouaké Ad")
        r = self.client.get(f"/ads/?city={self.city.slug}")
        self.assertContains(r, "Abidjan Ad")
        self.assertNotContains(r, "Bouaké Ad")

    def test_filter_by_category(self):
        make_ad(self.user, self.city, title="Ad Escorte Unique XZ9", category=Ad.Category.ESCORTE_GIRL)
        make_ad(self.user, self.city, title="Ad Trans Unique XZ9", category=Ad.Category.TRANSGENRE)
        r = self.client.get("/ads/?category=escorte_girl")
        self.assertContains(r, "Ad Escorte Unique XZ9")
        self.assertNotContains(r, "Ad Trans Unique XZ9")

    def test_filter_by_provider_username(self):
        u2 = make_user("u2", "u2@test.com")
        make_ad(self.user, self.city, title="User1 Ad")
        make_ad(u2, self.city, title="User2 Ad")
        r = self.client.get(f"/ads/?provider={self.user.username}")
        self.assertContains(r, "User1 Ad")
        self.assertNotContains(r, "User2 Ad")

    def test_filter_by_provider_id_ignored(self):
        """Le filtre par ID numérique est désactivé (prévient l'énumération)."""
        u2 = make_user("u2", "u2@test.com")
        make_ad(self.user, self.city, title="User1 Ad")
        make_ad(u2, self.city, title="User2 Ad")
        # Passer un ID entier → ignoré → toutes les annonces actives visibles
        r = self.client.get(f"/ads/?provider={self.user.pk}")
        self.assertContains(r, "User1 Ad")
        self.assertContains(r, "User2 Ad")

    def test_search_by_title(self):
        make_ad(self.user, self.city, title="Massage doux cocody")
        make_ad(self.user, self.city, title="Autre annonce")
        r = self.client.get("/ads/?q=massage")
        self.assertContains(r, "Massage doux cocody")
        self.assertNotContains(r, "Autre annonce")

    def test_search_by_description(self):
        make_ad(self.user, self.city, title="Annonce", description_sanitized="service premium discret")
        r = self.client.get("/ads/?q=discret")
        self.assertContains(r, "Annonce")

    def test_expired_ads_appear_after_active(self):
        make_ad(self.user, self.city, title="Active")
        make_ad(self.user, self.city, title="Expirée", status=Ad.Status.EXPIRED)
        r = self.client.get("/ads/")
        content = r.content.decode()
        self.assertGreater(content.find("Expirée"), content.find("Active"))

    def test_pagination_page2(self):
        for i in range(12):
            make_ad(self.user, self.city, title=f"Ad {i}")
        r = self.client.get("/ads/?page=2")
        self.assertEqual(r.status_code, 200)

    def test_invalid_city_slug_ignored(self):
        r = self.client.get("/ads/?city=slug-inexistant")
        self.assertEqual(r.status_code, 200)

    def test_boosted_ads_have_yellow_background(self):
        make_ad(self.user, self.city, title="Boostée", is_premium=True)
        r = self.client.get("/ads/")
        self.assertContains(r, "fefce8")


# ═══════════════════════════════════════════════════════════════════════════════
# VUE : ad_detail
# ═══════════════════════════════════════════════════════════════════════════════

@override_settings(CACHES={"default": {"BACKEND": "django.core.cache.backends.dummy.DummyCache"}})
class AdDetailViewTest(TestCase):
    def setUp(self):
        self.client = Client()
        self.client.cookies["age_gate_accepted"] = "1"
        self.user = make_user()
        self.city = make_city()

    def test_approved_ad_200(self):
        ad = make_ad(self.user, self.city)
        r = self.client.get(f"/ads/{ad.slug}/")
        self.assertEqual(r.status_code, 200)
        self.assertContains(r, ad.title)

    def test_expired_ad_accessible_not_404(self):
        ad = make_ad(self.user, self.city, status=Ad.Status.EXPIRED)
        r = self.client.get(f"/ads/{ad.slug}/")
        self.assertEqual(r.status_code, 200)

    def test_archived_ad_returns_410(self):
        ad = make_ad(self.user, self.city, status=Ad.Status.ARCHIVED)
        r = self.client.get(f"/ads/{ad.slug}/")
        self.assertEqual(r.status_code, 410)

    def test_draft_ad_returns_404(self):
        ad = make_ad(self.user, self.city, status=Ad.Status.DRAFT)
        r = self.client.get(f"/ads/{ad.slug}/")
        self.assertEqual(r.status_code, 404)

    def test_rejected_ad_returns_404(self):
        ad = make_ad(self.user, self.city, status=Ad.Status.REJECTED)
        r = self.client.get(f"/ads/{ad.slug}/")
        self.assertEqual(r.status_code, 404)

    def test_unprocessed_image_returns_404(self):
        ad = make_ad(self.user, self.city, image_processing_done=False)
        r = self.client.get(f"/ads/{ad.slug}/")
        self.assertEqual(r.status_code, 404)

    def test_unknown_slug_returns_404(self):
        r = self.client.get("/ads/slug-qui-nexiste-pas/")
        self.assertEqual(r.status_code, 404)

    def test_similar_ads_same_category_shown(self):
        ad = make_ad(self.user, self.city, title="Principale", category=Ad.Category.ESCORTE_GIRL)
        make_ad(self.user, self.city, title="Similaire", category=Ad.Category.ESCORTE_GIRL)
        r = self.client.get(f"/ads/{ad.slug}/")
        self.assertContains(r, "Similaire")

    def test_similar_ads_different_category_hidden(self):
        ad = make_ad(self.user, self.city, title="Principale", category=Ad.Category.ESCORTE_GIRL)
        make_ad(self.user, self.city, title="Autre catégorie", category=Ad.Category.ESCORTE_BOY)
        r = self.client.get(f"/ads/{ad.slug}/")
        self.assertNotContains(r, "Autre catégorie")

    def test_is_favorited_false_for_anonymous(self):
        ad = make_ad(self.user, self.city)
        r = self.client.get(f"/ads/{ad.slug}/")
        self.assertFalse(r.context["is_favorited"])

    def test_is_favorited_true_for_owner_of_favorite(self):
        u2 = make_user("u2", "u2@t.com")
        ad = make_ad(self.user, self.city)
        Favorite.objects.create(user=u2, ad=ad)
        self.client.force_login(u2)
        r = self.client.get(f"/ads/{ad.slug}/")
        self.assertTrue(r.context["is_favorited"])


# ═══════════════════════════════════════════════════════════════════════════════
# VUE : record_ad_view
# ═══════════════════════════════════════════════════════════════════════════════

class RecordAdViewTest(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = make_user()
        self.city = make_city()
        self.ad = make_ad(self.user, self.city)

    def test_first_view_recorded(self):
        r = self.client.post(f"/ads/{self.ad.slug}/record-view/")
        self.assertEqual(r.status_code, 200)
        data = json.loads(r.content)
        self.assertTrue(data["recorded"])
        self.ad.refresh_from_db()
        self.assertEqual(self.ad.views_count, 1)

    def test_duplicate_in_same_session_not_counted(self):
        self.client.post(f"/ads/{self.ad.slug}/record-view/")
        self.client.post(f"/ads/{self.ad.slug}/record-view/")
        self.ad.refresh_from_db()
        self.assertEqual(self.ad.views_count, 1)

    def test_owner_view_not_counted(self):
        self.client.force_login(self.user)
        r = self.client.post(f"/ads/{self.ad.slug}/record-view/")
        data = json.loads(r.content)
        self.assertFalse(data["recorded"])
        self.assertEqual(data.get("reason"), "owner")
        self.ad.refresh_from_db()
        self.assertEqual(self.ad.views_count, 0)

    def test_other_user_view_counted(self):
        u2 = make_user("u2", "u2@t.com")
        self.client.force_login(u2)
        self.client.post(f"/ads/{self.ad.slug}/record-view/")
        self.ad.refresh_from_db()
        self.assertEqual(self.ad.views_count, 1)

    def test_get_method_returns_405(self):
        r = self.client.get(f"/ads/{self.ad.slug}/record-view/")
        self.assertEqual(r.status_code, 405)

    def test_unknown_slug_returns_404(self):
        r = self.client.post("/ads/nope/record-view/")
        self.assertEqual(r.status_code, 404)

    def test_returns_ok_true(self):
        r = self.client.post(f"/ads/{self.ad.slug}/record-view/")
        data = json.loads(r.content)
        self.assertTrue(data["ok"])


# ═══════════════════════════════════════════════════════════════════════════════
# VUE : toggle_favorite
# ═══════════════════════════════════════════════════════════════════════════════

class ToggleFavoriteTest(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = make_user()
        self.city = make_city()
        self.ad = make_ad(self.user, self.city)

    def test_anonymous_redirects_to_login(self):
        r = self.client.post(f"/ads/favorites/toggle/{self.ad.pk}/")
        self.assertEqual(r.status_code, 302)
        self.assertIn("login", r["Location"])

    def test_add_favorite(self):
        self.client.force_login(self.user)
        r = self.client.post(f"/ads/favorites/toggle/{self.ad.pk}/")
        self.assertEqual(r.status_code, 200)
        data = json.loads(r.content)
        self.assertTrue(data["favorited"])
        self.assertTrue(Favorite.objects.filter(user=self.user, ad=self.ad).exists())

    def test_remove_existing_favorite(self):
        Favorite.objects.create(user=self.user, ad=self.ad)
        self.client.force_login(self.user)
        r = self.client.post(f"/ads/favorites/toggle/{self.ad.pk}/")
        data = json.loads(r.content)
        self.assertFalse(data["favorited"])
        self.assertFalse(Favorite.objects.filter(user=self.user, ad=self.ad).exists())

    def test_toggle_expired_ad_works(self):
        expired = make_ad(self.user, self.city, title="Exp", status=Ad.Status.EXPIRED)
        self.client.force_login(self.user)
        r = self.client.post(f"/ads/favorites/toggle/{expired.pk}/")
        self.assertEqual(r.status_code, 200)

    def test_toggle_draft_returns_404(self):
        draft = make_ad(self.user, self.city, title="Draft", status=Ad.Status.DRAFT)
        self.client.force_login(self.user)
        r = self.client.post(f"/ads/favorites/toggle/{draft.pk}/")
        self.assertEqual(r.status_code, 404)

    def test_favorites_list_accessible(self):
        Favorite.objects.create(user=self.user, ad=self.ad)
        self.client.force_login(self.user)
        self.client.cookies["age_gate_accepted"] = "1"
        r = self.client.get("/ads/favorites/")
        self.assertEqual(r.status_code, 200)


# ═══════════════════════════════════════════════════════════════════════════════
# VUE : search_suggestions
# ═══════════════════════════════════════════════════════════════════════════════

@override_settings(CACHES={"default": {"BACKEND": "django.core.cache.backends.dummy.DummyCache"}})
class SearchSuggestionsTest(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = make_user()
        self.city = make_city()

    def test_short_query_returns_empty(self):
        r = self.client.get("/ads/api/search-suggestions/?q=a")
        data = json.loads(r.content)
        self.assertEqual(data["suggestions"], [])

    def test_no_query_returns_empty(self):
        r = self.client.get("/ads/api/search-suggestions/")
        data = json.loads(r.content)
        self.assertEqual(data["suggestions"], [])

    def test_title_match_returned(self):
        make_ad(self.user, self.city, title="Massage relaxant cocody")
        r = self.client.get("/ads/api/search-suggestions/?q=massage")
        data = json.loads(r.content)
        labels = [s["label"] for s in data["suggestions"]]
        self.assertTrue(any("assage" in l for l in labels))

    def test_category_match_returned(self):
        r = self.client.get("/ads/api/search-suggestions/?q=escorte")
        data = json.loads(r.content)
        types = [s["type"] for s in data["suggestions"]]
        self.assertIn("category", types)

    def test_subcategory_match_returned(self):
        r = self.client.get("/ads/api/search-suggestions/?q=massage")
        data = json.loads(r.content)
        types = [s["type"] for s in data["suggestions"]]
        self.assertIn("subcategory", types)

    def test_max_15_results(self):
        for i in range(20):
            make_ad(self.user, self.city, title=f"Annonce massage {i}")
        r = self.client.get("/ads/api/search-suggestions/?q=massage")
        data = json.loads(r.content)
        self.assertLessEqual(len(data["suggestions"]), 15)


# ═══════════════════════════════════════════════════════════════════════════════
# TÂCHES CELERY
# ═══════════════════════════════════════════════════════════════════════════════

class ExpireAdsTaskTest(TestCase):
    def setUp(self):
        self.user = make_user()
        self.city = make_city()

    @patch("accounts.email_service.EmailService.send_email")
    def test_expires_overdue_approved_ad(self, mock_email):
        ad = make_ad(self.user, self.city, expires_at=timezone.now() - timedelta(hours=1))
        expire_ads()
        ad.refresh_from_db()
        self.assertEqual(ad.status, Ad.Status.EXPIRED)

    @patch("accounts.email_service.EmailService.send_email")
    def test_returns_count_string(self, mock_email):
        make_ad(self.user, self.city, expires_at=timezone.now() - timedelta(hours=1))
        result = expire_ads()
        self.assertIn("1", result)

    @patch("accounts.email_service.EmailService.send_email")
    def test_does_not_expire_future_ad(self, mock_email):
        ad = make_ad(self.user, self.city, expires_at=timezone.now() + timedelta(days=3))
        expire_ads()
        ad.refresh_from_db()
        self.assertEqual(ad.status, Ad.Status.APPROVED)

    @patch("accounts.email_service.EmailService.send_email")
    def test_does_not_expire_already_expired(self, mock_email):
        make_ad(self.user, self.city,
                expires_at=timezone.now() - timedelta(days=2),
                status=Ad.Status.EXPIRED)
        result = expire_ads()
        self.assertIn("0", result)

    @patch("accounts.email_service.EmailService.send_email")
    def test_email_sent_on_expiry(self, mock_email):
        make_ad(self.user, self.city, expires_at=timezone.now() - timedelta(hours=1))
        expire_ads()
        mock_email.assert_called_once()

    @patch("accounts.email_service.EmailService.send_email")
    def test_email_failure_does_not_block_expiry(self, mock_email):
        mock_email.side_effect = Exception("SMTP down")
        ad = make_ad(self.user, self.city, expires_at=timezone.now() - timedelta(hours=1))
        expire_ads()  # ne doit pas lever
        ad.refresh_from_db()
        self.assertEqual(ad.status, Ad.Status.EXPIRED)

    @patch("accounts.email_service.EmailService.send_email")
    def test_multiple_ads_expired_together(self, mock_email):
        for _ in range(3):
            make_ad(self.user, self.city, expires_at=timezone.now() - timedelta(hours=1))
        result = expire_ads()
        self.assertIn("3", result)


class PurgeExpiredAdsTaskTest(TestCase):
    def setUp(self):
        self.user = make_user()
        self.city = make_city()

    def test_purges_ads_older_than_50_days(self):
        ad = make_ad(self.user, self.city,
                     status=Ad.Status.EXPIRED,
                     expires_at=timezone.now() - timedelta(days=51))
        purge_expired_ads()
        self.assertFalse(Ad.objects.filter(pk=ad.pk).exists())

    def test_keeps_ads_within_50_days(self):
        ad = make_ad(self.user, self.city,
                     status=Ad.Status.EXPIRED,
                     expires_at=timezone.now() - timedelta(days=49))
        purge_expired_ads()
        self.assertTrue(Ad.objects.filter(pk=ad.pk).exists())

    def test_boundary_exactly_50_days_purged(self):
        ad = make_ad(self.user, self.city,
                     status=Ad.Status.EXPIRED,
                     expires_at=timezone.now() - timedelta(days=50, seconds=1))
        purge_expired_ads()
        self.assertFalse(Ad.objects.filter(pk=ad.pk).exists())

    def test_approved_ad_not_purged(self):
        ad = make_ad(self.user, self.city,
                     status=Ad.Status.APPROVED,
                     expires_at=timezone.now() - timedelta(days=60))
        purge_expired_ads()
        self.assertTrue(Ad.objects.filter(pk=ad.pk).exists())

    def test_returns_count_string(self):
        make_ad(self.user, self.city,
                status=Ad.Status.EXPIRED,
                expires_at=timezone.now() - timedelta(days=55))
        result = purge_expired_ads()
        self.assertIn("1", result)


class NotifyExpiringSoonTaskTest(TestCase):
    def setUp(self):
        self.user = make_user()
        self.city = make_city()

    @patch("accounts.email_service.EmailService.send_email")
    def test_24h_notification_sent_in_window(self, mock_email):
        ad = make_ad(self.user, self.city,
                     expires_at=timezone.now() + timedelta(hours=24),
                     expiry_notified_24h=False)
        notify_expiring_soon_24h()
        mock_email.assert_called_once()
        ad.refresh_from_db()
        self.assertTrue(ad.expiry_notified_24h)

    @patch("accounts.email_service.EmailService.send_email")
    def test_24h_notification_not_sent_twice(self, mock_email):
        make_ad(self.user, self.city,
                expires_at=timezone.now() + timedelta(hours=24),
                expiry_notified_24h=True)
        notify_expiring_soon_24h()
        mock_email.assert_not_called()

    @patch("accounts.email_service.EmailService.send_email")
    def test_1h_notification_sent_in_window(self, mock_email):
        ad = make_ad(self.user, self.city,
                     expires_at=timezone.now() + timedelta(minutes=60),
                     expiry_notified_1h=False)
        notify_expiring_soon_1h()
        mock_email.assert_called_once()
        ad.refresh_from_db()
        self.assertTrue(ad.expiry_notified_1h)

    @patch("accounts.email_service.EmailService.send_email")
    def test_1h_notification_not_sent_twice(self, mock_email):
        make_ad(self.user, self.city,
                expires_at=timezone.now() + timedelta(minutes=60),
                expiry_notified_1h=True)
        notify_expiring_soon_1h()
        mock_email.assert_not_called()


class BoostTasksTest(TestCase):
    def setUp(self):
        self.user = make_user()
        self.city = make_city()

    def test_promote_boosted_sets_premium(self):
        ad = make_ad(self.user, self.city,
                     is_boosted=True,
                     boost_expires_at=timezone.now() + timedelta(days=30),
                     is_premium=False)
        promote_boosted_ads()
        ad.refresh_from_db()
        self.assertTrue(ad.is_premium)
        self.assertIsNotNone(ad.premium_until)

    def test_promote_expired_boost_not_touched(self):
        ad = make_ad(self.user, self.city,
                     is_boosted=True,
                     boost_expires_at=timezone.now() - timedelta(days=1),
                     is_premium=False)
        promote_boosted_ads()
        ad.refresh_from_db()
        self.assertFalse(ad.is_premium)

    def test_expire_premium_removes_flag(self):
        ad = make_ad(self.user, self.city,
                     is_premium=True,
                     premium_until=timezone.now() - timedelta(minutes=5))
        expire_premium_ads()
        ad.refresh_from_db()
        self.assertFalse(ad.is_premium)

    def test_expire_premium_keeps_active(self):
        ad = make_ad(self.user, self.city,
                     is_premium=True,
                     premium_until=timezone.now() + timedelta(hours=2))
        expire_premium_ads()
        ad.refresh_from_db()
        self.assertTrue(ad.is_premium)
