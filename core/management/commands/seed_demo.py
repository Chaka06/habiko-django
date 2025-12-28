import io
from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from django.core.files.base import ContentFile
from django.utils import timezone
from ads.models import City, Ad, AdMedia

try:
    from PIL import Image
except Exception:  # pragma: no cover
    Image = None


class Command(BaseCommand):
    help = "Crée des données de démonstration: villes, prestataire, annonces approuvées"

    def handle(self, *args, **options):
        User = get_user_model()

        # Villes CI
        cities = [
            ("Abidjan", "Lagunes"),
            ("Bouaké", "Gbêkê"),
            ("Yamoussoukro", "Lacs"),
            ("San-Pédro", "Bas-Sassandra"),
        ]
        city_objs = []
        for name, region in cities:
            obj, _ = City.objects.get_or_create(name=name, defaults={"region": region})
            city_objs.append(obj)

        # Prestataire de démo
        user, _ = User.objects.get_or_create(
            username="demo_provider",
            defaults={
                "email": "provider@example.com",
                "role": "provider",
                "is_active": True,
            },
        )
        if not user.has_usable_password():
            user.set_password("demopass123")
            user.save()

        # Générer petite image en mémoire
        img_content = None
        if Image is not None:
            buf = io.BytesIO()
            image = Image.new("RGB", (600, 400), color=(230, 230, 230))
            image.save(buf, format="JPEG", quality=70)
            img_content = buf.getvalue()

        examples = [
            {
                "title": "Discrète et élégante à Abidjan",
                "category": Ad.Category.ESCORTE_GIRL,
                "city": city_objs[0],
                "area": "Cocody",
                "subcategories": ["massage africain", "fellation"],
            },
            {
                "title": "Gentleman attentionné",
                "category": Ad.Category.ESCORTE_BOY,
                "city": city_objs[1],
                "area": "Zone 3",
                "subcategories": ["massage sexuel"],
            },
            {
                "title": "Expérience premium transgenre",
                "category": Ad.Category.TRANSGENRE,
                "city": city_objs[2],
                "area": "Centre",
                "subcategories": ["vaginal"],
            },
        ]

        created = 0
        for data in examples:
            ad, _ = Ad.objects.get_or_create(
                user=user,
                title=data["title"],
                defaults={
                    "description_sanitized": "Description soignée, pas de contenu explicite.",
                    "category": data["category"],
                    "city": data["city"],
                    "area": data["area"],
                    "status": Ad.Status.APPROVED,
                    "subcategories": data["subcategories"],
                    "expires_at": timezone.now() + timezone.timedelta(days=30),
                },
            )
            # Média principal
            if not ad.media.exists() and img_content is not None:
                AdMedia.objects.create(
                    ad=ad,
                    image=ContentFile(img_content, name="demo.jpg"),
                    is_primary=True,
                )
            created += 1

        self.stdout.write(
            self.style.SUCCESS(f"Données de démo créées/actualisées ({created} annonces).")
        )
