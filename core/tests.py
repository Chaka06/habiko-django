from django.test import TestCase, Client
from django.contrib.auth import get_user_model
from ads.models import City, Ad

User = get_user_model()


class LandingViewTest(TestCase):
    def setUp(self):
        self.client = Client()
        self.city = City.objects.create(name="Abidjan", region="Lagunes")
        self.user = User.objects.create_user(
            username="testuser", email="test@example.com", password="testpass123"
        )
        self.ad = Ad.objects.create(
            user=self.user,
            title="Test Ad",
            description_sanitized="Test description",
            category=Ad.Category.RENCONTRES_ESCORTES,
            city=self.city,
            status=Ad.Status.APPROVED,
        )

    def test_landing_page_loads(self):
        self.client.cookies["age_gate_accepted"] = "1"
        response = self.client.get("/")
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "KIABA")

    def test_landing_shows_cities(self):
        self.client.cookies["age_gate_accepted"] = "1"
        response = self.client.get("/")
        self.assertContains(response, "Abidjan")

    def test_landing_shows_recent_ads(self):
        self.client.cookies["age_gate_accepted"] = "1"
        response = self.client.get("/")
        self.assertContains(response, "Test Ad")


class AgeGateTest(TestCase):
    def setUp(self):
        self.client = Client()

    def test_age_gate_redirects_without_cookie(self):
        response = self.client.get("/")
        self.assertRedirects(response, "/age-gate/")

    def test_age_gate_allows_access_with_cookie(self):
        self.client.cookies["age_gate_accepted"] = "1"
        response = self.client.get("/")
        self.assertEqual(response.status_code, 200)

    def test_age_gate_post_sets_cookie(self):
        response = self.client.post("/age-gate/")
        self.assertRedirects(response, "/")
        self.assertEqual(self.client.cookies["age_gate_accepted"].value, "1")
