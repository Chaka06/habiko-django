from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from ads.models import Ad, City
from accounts.models import Profile
from django.utils import timezone


class Command(BaseCommand):
    help = "Créer des annonces de test pour la modération"

    def handle(self, *args, **options):
        User = get_user_model()

        # Créer un utilisateur de test si pas existant
        user, created = User.objects.get_or_create(
            username="test_provider",
            defaults={
                "email": "test@kiaba.local",
                "role": "provider",
                "phone_e164": "+225123456789",
            },
        )

        if created:
            Profile.objects.create(
                user=user,
                display_name="Test Provider",
                phone_e164="+225123456789",
                contact_prefs=["sms", "whatsapp", "call"],
            )
            self.stdout.write("Utilisateur de test créé")

        # Récupérer une ville
        city = City.objects.first()
        if not city:
            self.stdout.write(
                self.style.ERROR(
                    "Aucune ville trouvée. Lancez d'abord 'python manage.py seed_cities'"
                )
            )
            return

        # Créer des annonces avec différents statuts
        ads_data = [
            {
                "title": "Annonce en attente de modération",
                "description": "Description de test pour modération",
                "category": Ad.Category.RENCONTRES_ESCORTES,
                "subcategories": ["vaginal", "fellation"],
                "status": Ad.Status.PENDING,
            },
            {
                "title": "Annonce approuvée",
                "description": "Description d'une annonce approuvée",
                "category": Ad.Category.MASSAGES_SERVICES,
                "subcategories": ["Massage Relaxant"],
                "status": Ad.Status.APPROVED,
            },
            {
                "title": "Annonce rejetée",
                "description": "Description d'une annonce rejetée",
                "category": Ad.Category.PRODUITS_ADULTES,
                "subcategories": ["Sextoy - Jouet Sexuel"],
                "status": Ad.Status.REJECTED,
            },
        ]

        for ad_data in ads_data:
            ad, created = Ad.objects.get_or_create(
                title=ad_data["title"],
                defaults={
                    "user": user,
                    "description_sanitized": ad_data["description"],
                    "category": ad_data["category"],
                    "subcategories": ad_data["subcategories"],
                    "city": city,
                    "status": ad_data["status"],
                    "expires_at": timezone.now() + timezone.timedelta(days=14),
                },
            )

            if created:
                self.stdout.write(f"Annonce créée: {ad.title} ({ad.status})")
            else:
                self.stdout.write(f"Annonce existante: {ad.title} ({ad.status})")

        self.stdout.write(self.style.SUCCESS("Données de test de modération créées avec succès !"))
        self.stdout.write("Connectez-vous sur /admin pour tester la modération.")
