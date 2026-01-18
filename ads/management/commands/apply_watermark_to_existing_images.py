"""
Commande pour appliquer le filigrane aux images existantes
"""
import os
from django.core.management.base import BaseCommand
from ads.models import AdMedia
from django.db import transaction
from django.conf import settings


class Command(BaseCommand):
    help = "Applique le filigrane du logo à toutes les images existantes qui n'en ont pas encore"

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Affiche ce qui sera fait sans modifier les images',
        )
        parser.add_argument(
            '--limit',
            type=int,
            default=None,
            help='Limite le nombre d\'images à traiter',
        )

    def handle(self, *args, **options):
        dry_run = options['dry_run']
        limit = options['limit']
        
        # Vérifier que le logo existe
        logo_path = None
        if hasattr(settings, 'STATICFILES_DIRS') and settings.STATICFILES_DIRS:
            for static_dir in settings.STATICFILES_DIRS:
                potential_path = os.path.join(str(static_dir), 'img', 'logo.png')
                if os.path.exists(potential_path):
                    logo_path = potential_path
                    break
        
        if not logo_path:
            logo_path = os.path.join(settings.BASE_DIR, 'static', 'img', 'logo.png')
        
        if not os.path.exists(logo_path):
            self.stdout.write(
                self.style.ERROR(f"✗ Logo introuvable à: {logo_path}")
            )
            self.stdout.write("Vérifiez que le fichier static/img/logo.png existe.")
            return
        
        self.stdout.write(f"Logo trouvé: {logo_path}")
        
        # Récupérer toutes les images
        all_media = AdMedia.objects.all()
        if limit:
            all_media = all_media[:limit]
        
        total = all_media.count()
        self.stdout.write(f"Traitement de {total} image(s)...")
        
        processed = 0
        errors = 0
        
        for media in all_media:
            try:
                if not media.image:
                    continue
                
                # Vérifier que le fichier existe
                if hasattr(media.image, 'path'):
                    if not os.path.exists(media.image.path):
                        self.stdout.write(
                            self.style.WARNING(f"  ⚠ Fichier introuvable: {media.image.name}")
                        )
                        errors += 1
                        continue
                
                # Réinitialiser le flag pour forcer l'application du filigrane
                media._watermark_applied = False
                
                if dry_run:
                    self.stdout.write(f"  [DRY-RUN] Traiterait: {media.image.name} (Ad #{media.ad_id})")
                else:
                    # Afficher le chemin de l'image pour debug
                    image_path = media.image.path if hasattr(media.image, 'path') else media.image.name
                    self.stdout.write(f"  Traitement: {image_path}")
                    
                    # Appliquer le filigrane
                    result = media._add_watermark()
                    if result:
                        # Sauvegarder l'image modifiée (même si le fichier a été écrit directement)
                        # Cela met à jour les métadonnées dans la base de données
                        media.save(update_fields=[])  # Sauvegarder sans mettre à jour de champs spécifiques
                        processed += 1
                        self.stdout.write(
                            self.style.SUCCESS(f"  ✓ Filigrane appliqué: {media.image.name} (Ad #{media.ad_id})")
                        )
                    else:
                        self.stdout.write(
                            self.style.WARNING(f"  ⚠ Impossible d'appliquer le filigrane: {media.image.name}")
                        )
                        errors += 1
                        
            except Exception as e:
                errors += 1
                self.stdout.write(
                    self.style.ERROR(f"  ✗ Erreur pour {media.image.name if media.image else 'image inconnue'}: {str(e)}")
                )
        
        if dry_run:
            self.stdout.write(self.style.WARNING(f"\n[DRY-RUN] {total} image(s) seraient traitées"))
        else:
            self.stdout.write(self.style.SUCCESS(f"\n✓ {processed} image(s) traitées avec succès"))
            if errors > 0:
                self.stdout.write(self.style.WARNING(f"⚠ {errors} erreur(s) rencontrée(s)"))

