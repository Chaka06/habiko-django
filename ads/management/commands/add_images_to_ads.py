"""
Commande pour ajouter des images aux annonces immobilières
"""
from django.core.management.base import BaseCommand
from django.core.files.base import ContentFile
from ads.models import Ad, AdMedia
import requests
from io import BytesIO
import random

# URLs d'images d'immobilier libres de droits (Unsplash - URLs testées et fonctionnelles)
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
    "https://images.unsplash.com/photo-1600607688969-a5fcd52667ce?w=800&auto=format&fit=crop",  # Maison classique
    "https://images.unsplash.com/photo-1600585152915-d208bec867a1?w=800&auto=format&fit=crop",  # Extérieur 2
    "https://images.unsplash.com/photo-1600047509807-ba8f99d2cdde?w=800&auto=format&fit=crop",  # Piscine 2
]


class Command(BaseCommand):
    help = "Ajoute des images aux annonces immobilières existantes"

    def add_arguments(self, parser):
        parser.add_argument(
            "--all",
            action="store_true",
            help="Ajouter des images à toutes les annonces",
        )
        parser.add_argument(
            "--count",
            type=int,
            default=3,
            help="Nombre d'images par annonce (défaut: 3)",
        )

    def handle(self, *args, **options):
        add_all = options["all"]
        images_per_ad = options["count"]
        
        if add_all:
            ads = Ad.objects.filter(status=Ad.Status.APPROVED)
        else:
            # Prendre les annonces sans images
            ads = Ad.objects.filter(
                status=Ad.Status.APPROVED,
                media__isnull=True
            ).distinct()
        
        if not ads.exists():
            self.stdout.write(
                self.style.WARNING("Aucune annonce trouvée.")
            )
            return
        
        self.stdout.write(
            f"Ajout d'images à {ads.count()} annonce(s)..."
        )
        
        added_count = 0
        for ad in ads:
            # Vérifier si l'annonce a déjà des images
            existing_images = ad.media.count()
            if existing_images > 0 and not add_all:
                self.stdout.write(
                    self.style.WARNING(
                        f"⚠️  {ad.title} a déjà {existing_images} image(s), ignorée."
                    )
                )
                continue
            
            # Déterminer combien d'images ajouter
            images_to_add = max(1, images_per_ad - existing_images)
            
            try:
                for i in range(images_to_add):
                    # Choisir une image aléatoire
                    image_url = random.choice(IMMOBILIER_IMAGES)
                    
                    # Télécharger l'image
                    response = requests.get(image_url, timeout=10)
                    response.raise_for_status()
                    
                    # Créer le fichier image
                    image_content = BytesIO(response.content)
                    image_name = f"ad_{ad.id}_image_{i+1}.jpg"
                    
                    # Créer l'AdMedia
                    ad_media = AdMedia.objects.create(
                        ad=ad,
                        image=ContentFile(image_content.read(), name=image_name),
                        is_primary=(i == 0 and existing_images == 0)
                    )
                    
                    added_count += 1
                    self.stdout.write(
                        self.style.SUCCESS(
                            f"  ✅ Image {i+1} ajoutée à: {ad.title}"
                        )
                    )
                
            except Exception as e:
                self.stdout.write(
                    self.style.ERROR(
                        f"  ❌ Erreur pour {ad.title}: {str(e)}"
                    )
                )
                continue
        
        self.stdout.write(
            self.style.SUCCESS(
                f"\n🎉 {added_count} image(s) ajoutée(s) avec succès !"
            )
        )

