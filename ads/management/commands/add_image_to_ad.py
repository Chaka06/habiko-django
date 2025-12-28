"""
Commande pour ajouter des images à une annonce spécifique
"""
from django.core.management.base import BaseCommand
from django.core.files.base import ContentFile
from ads.models import Ad, AdMedia
import requests
from io import BytesIO

# URLs d'images d'immobilier libres de droits (Unsplash)
IMMOBILIER_IMAGES = [
    "https://images.unsplash.com/photo-1568605114967-8130f3a36994?w=800&auto=format&fit=crop",  # Maison moderne
    "https://images.unsplash.com/photo-1564013799919-ab600027ffc6?w=800&auto=format&fit=crop",  # Villa
    "https://images.unsplash.com/photo-1600596542815-ffad4c1539a9?w=800&auto=format&fit=crop",  # Maison avec jardin
    "https://images.unsplash.com/photo-1600585154340-be6161a56a0c?w=800&auto=format&fit=crop",  # Appartement moderne
    "https://images.unsplash.com/photo-1600607687939-ce8a6c25118c?w=800&auto=format&fit=crop",  # Intérieur moderne
    "https://images.unsplash.com/photo-1600566753190-17f0baa2a6c3?w=800&auto=format&fit=crop",  # Cuisine moderne
    "https://images.unsplash.com/photo-1600585154526-990dced4db0d?w=800&auto=format&fit=crop",  # Salon moderne
    "https://images.unsplash.com/photo-1600607687920-4e2a09cf159d?w=800&auto=format&fit=crop",  # Terrasse
    "https://images.unsplash.com/photo-1600566753086-00f18fb6b3ea?w=800&auto=format&fit=crop",  # Jardin
    "https://images.unsplash.com/photo-1600585152915-d208bec867a1?w=800&auto=format&fit=crop",  # Extérieur maison
    "https://images.unsplash.com/photo-1600047509807-ba8f99d2cdde?w=800&auto=format&fit=crop",  # Piscine
    "https://images.unsplash.com/photo-1600047509358-9dc75507daeb?w=800&auto=format&fit=crop",  # Terrain
    "https://images.unsplash.com/photo-1600566752355-35792bedcfea?w=800&auto=format&fit=crop",  # Salle de bain
    "https://images.unsplash.com/photo-1600210492486-724fe5c67fb0?w=800&auto=format&fit=crop",  # Chambre moderne
]


class Command(BaseCommand):
    help = "Ajoute des images à une annonce spécifique"

    def add_arguments(self, parser):
        parser.add_argument(
            "--title",
            type=str,
            help="Titre de l'annonce",
        )
        parser.add_argument(
            "--count",
            type=int,
            default=3,
            help="Nombre d'images à ajouter (défaut: 3)",
        )

    def handle(self, *args, **options):
        title = options.get("title")
        count = options.get("count", 3)
        
        if not title:
            self.stdout.write(
                self.style.ERROR("Veuillez spécifier le titre de l'annonce avec --title")
            )
            return
        
        try:
            ad = Ad.objects.get(title=title)
        except Ad.DoesNotExist:
            self.stdout.write(
                self.style.ERROR(f"Annonce non trouvée: {title}")
            )
            return
        
        existing_count = ad.media.count()
        if existing_count >= 5:
            self.stdout.write(
                self.style.WARNING(
                    f"L'annonce a déjà {existing_count} images (maximum 5)."
                )
            )
            return
        
        images_to_add = min(count, 5 - existing_count)
        
        self.stdout.write(
            f"Ajout de {images_to_add} image(s) à: {ad.title}"
        )
        
        added = 0
        import random
        for i in range(images_to_add):
            try:
                image_url = random.choice(IMMOBILIER_IMAGES)
                response = requests.get(image_url, timeout=10)
                response.raise_for_status()
                
                image_content = BytesIO(response.content)
                image_name = f"ad_{ad.id}_image_{existing_count + i + 1}.jpg"
                
                ad_media = AdMedia.objects.create(
                    ad=ad,
                    image=ContentFile(image_content.read(), name=image_name),
                    is_primary=(existing_count == 0 and i == 0)
                )
                
                added += 1
                self.stdout.write(
                    self.style.SUCCESS(f"  ✅ Image {i+1} ajoutée")
                )
                
            except Exception as e:
                self.stdout.write(
                    self.style.ERROR(f"  ❌ Erreur: {str(e)}")
                )
                continue
        
        self.stdout.write(
            self.style.SUCCESS(
                f"\n🎉 {added} image(s) ajoutée(s) avec succès à '{ad.title}' !"
            )
        )

