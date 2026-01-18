from django.test import TestCase
from django.contrib.auth import get_user_model
from .models import Profile

User = get_user_model()


class CustomUserModelTest(TestCase):
    def test_create_user(self):
        user = User.objects.create_user(
            username="testuser", email="test@example.com", password="testpass123"
        )
        self.assertEqual(user.username, "testuser")
        self.assertEqual(user.role, "provider")
        self.assertFalse(user.is_verified)

    def test_create_superuser(self):
        user = User.objects.create_superuser(
            username="admin", email="admin@example.com", password="adminpass123"
        )
        self.assertTrue(user.is_superuser)
        self.assertTrue(user.is_staff)


class ProfileModelTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="testuser", email="test@example.com", password="testpass123"
        )

    def test_profile_auto_creation(self):
        """Test que le profil est créé automatiquement"""
        self.assertTrue(Profile.objects.filter(user=self.user).exists())
        profile = Profile.objects.get(user=self.user)
        self.assertEqual(profile.display_name, "testuser")
        self.assertEqual(profile.country, "CI")

    def test_contact_prefs_default(self):
        profile = Profile.objects.get(user=self.user)
        self.assertEqual(profile.contact_prefs, [])
