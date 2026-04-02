"""
Commande pour supprimer toutes les images des annonces
"""
from django.core.management.base import BaseCommand
from ads.models import AdMedia
import os
from django.conf import settings


class Command(BaseCommand):
    help = "Supprime toutes les images des annonces"

    def handle(self, *args, **options):
        # Compter les images
        total_images = AdMedia.objects.count()
        
        if total_images == 0:
            self.stdout.write(
                self.style.WARNING("Aucune image à supprimer.")
            )
            return
        
        self.stdout.write(
            f"Suppression de {total_images} image(s)..."
        )
        
        deleted_count = 0
        for ad_media in AdMedia.objects.all():
            try:
                # Supprimer le fichier physique si il existe
                if ad_media.image and hasattr(ad_media.image, 'path'):
                    try:
                        if os.path.exists(ad_media.image.path):
                            os.remove(ad_media.image.path)
                    except Exception as e:
                        self.stdout.write(
                            self.style.WARNING(
                                f"Impossible de supprimer le fichier {ad_media.image.path}: {e}"
                            )
                        )
                
                # Supprimer l'enregistrement de la base de données
                ad_media.delete()
                deleted_count += 1
                
            except Exception as e:
                self.stdout.write(
                    self.style.ERROR(
                        f"Erreur lors de la suppression: {e}"
                    )
                )
        
        self.stdout.write(
            self.style.SUCCESS(
                f"\n✅ {deleted_count} image(s) supprimée(s) avec succès !"
            )
        )

