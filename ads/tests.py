from django.test import TestCase
from django.core.exceptions import ValidationError
from django.contrib.auth import get_user_model
from .models import City, Ad, AdMedia

User = get_user_model()


class AdModelTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="testuser", email="test@example.com", password="testpass123"
        )
        self.city = City.objects.create(name="Abidjan", region="Lagunes")

    def test_create_ad(self):
        ad = Ad.objects.create(
            user=self.user,
            title="Test Ad",
            description_sanitized="Test description",
            category=Ad.Category.RENCONTRES_ESCORTES,
            city=self.city,
            area="Cocody",
        )
        self.assertEqual(ad.title, "Test Ad")
        self.assertEqual(ad.status, Ad.Status.DRAFT)
        self.assertTrue(ad.slug)

    def test_ad_slug_generation(self):
        ad1 = Ad.objects.create(
            user=self.user,
            title="Test Ad",
            description_sanitized="Test",
            category=Ad.Category.RENCONTRES_ESCORTES,
            city=self.city,
        )
        ad2 = Ad.objects.create(
            user=self.user,
            title="Test Ad",
            description_sanitized="Test",
            category=Ad.Category.RENCONTRES_ESCORTES,
            city=self.city,
        )
        self.assertNotEqual(ad1.slug, ad2.slug)
        self.assertTrue(ad2.slug.endswith("-2"))

    def test_subcategories_validation(self):
        ad = Ad(
            user=self.user,
            title="Test",
            description_sanitized="Test",
            category=Ad.Category.RENCONTRES_ESCORTES,
            city=self.city,
            subcategories=["invalid_subcategory"],
        )
        with self.assertRaises(ValidationError):
            ad.clean()

    def test_contacts_clicks_initialization(self):
        ad = Ad.objects.create(
            user=self.user,
            title="Test",
            description_sanitized="Test",
            category=Ad.Category.RENCONTRES_ESCORTES,
            city=self.city,
        )
        self.assertEqual(ad.contacts_clicks, {"sms": 0, "whatsapp": 0, "call": 0})


class AdMediaModelTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="testuser", email="test@example.com", password="testpass123"
        )
        self.city = City.objects.create(name="Abidjan")
        self.ad = Ad.objects.create(
            user=self.user,
            title="Test Ad",
            description_sanitized="Test",
            category=Ad.Category.RENCONTRES_ESCORTES,
            city=self.city,
        )

    def test_max_5_photos_validation(self):
        # Créer 5 médias
        for i in range(5):
            AdMedia.objects.create(ad=self.ad, image=f"test_{i}.jpg")

        # Le 6ème doit échouer
        with self.assertRaises(ValidationError):
            media = AdMedia(ad=self.ad, image="test_6.jpg")
            media.clean()

    def test_primary_media_unique(self):
        media1 = AdMedia.objects.create(ad=self.ad, image="test1.jpg", is_primary=True)
        media2 = AdMedia.objects.create(ad=self.ad, image="test2.jpg", is_primary=True)

        # Vérifier qu'un seul est primary après sauvegarde
        media1.refresh_from_db()
        media2.refresh_from_db()
        self.assertTrue(media2.is_primary)
        self.assertFalse(media1.is_primary)


class CityModelTest(TestCase):
    def test_create_city(self):
        city = City.objects.create(name="Abidjan", region="Lagunes")
        self.assertEqual(city.name, "Abidjan")
        self.assertEqual(city.slug, "abidjan")

    def test_slug_generation(self):
        city = City(name="Yamoussoukro")
        city.save()
        self.assertEqual(city.slug, "yamoussoukro")
