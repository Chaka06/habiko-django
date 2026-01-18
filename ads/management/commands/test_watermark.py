"""
Commande de test pour vérifier le filigrane sur une seule image
"""
import os
from django.core.management.base import BaseCommand
from ads.models import AdMedia
from django.conf import settings


class Command(BaseCommand):
    help = "Teste le filigrane sur une seule image"

    def add_arguments(self, parser):
        parser.add_argument(
            '--ad-id',
            type=int,
            help='ID de l\'annonce à tester',
        )
        parser.add_argument(
            '--media-id',
            type=int,
            help='ID du média à tester',
        )

    def handle(self, *args, **options):
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
            return
        
        self.stdout.write(f"✓ Logo trouvé: {logo_path}")
        self.stdout.write(f"  Taille: {os.path.getsize(logo_path)} bytes")
        
        # Trouver l'image à tester
        media = None
        if options['media_id']:
            try:
                media = AdMedia.objects.get(pk=options['media_id'])
            except AdMedia.DoesNotExist:
                self.stdout.write(self.style.ERROR(f"✗ Média #{options['media_id']} introuvable"))
                return
        elif options['ad_id']:
            media = AdMedia.objects.filter(ad_id=options['ad_id']).first()
            if not media:
                self.stdout.write(self.style.ERROR(f"✗ Aucune image trouvée pour l'annonce #{options['ad_id']}"))
                return
        else:
            # Prendre la première image disponible
            media = AdMedia.objects.first()
            if not media:
                self.stdout.write(self.style.ERROR("✗ Aucune image dans la base de données"))
                return
        
        if not media.image:
            self.stdout.write(self.style.ERROR("✗ L'image n'a pas de fichier"))
            return
        
        image_path = media.image.path if hasattr(media.image, 'path') else media.image.name
        self.stdout.write(f"\nImage à tester:")
        self.stdout.write(f"  ID: {media.id}")
        self.stdout.write(f"  Ad: #{media.ad_id}")
        self.stdout.write(f"  Chemin: {image_path}")
        
        if hasattr(media.image, 'path'):
            if os.path.exists(media.image.path):
                self.stdout.write(f"  Taille: {os.path.getsize(media.image.path)} bytes")
            else:
                self.stdout.write(self.style.ERROR(f"  ✗ Fichier introuvable sur le disque"))
                return
        
        # Appliquer le filigrane
        self.stdout.write(f"\nApplication du filigrane...")
        media._watermark_applied = False
        result = media._add_watermark()
        
        if result:
            self.stdout.write(self.style.SUCCESS("✓ Filigrane appliqué avec succès!"))
            self.stdout.write(f"\nVérifiez maintenant l'image: {image_path}")
            self.stdout.write("Si le filigrane n'apparaît pas:")
            self.stdout.write("  1. Videz le cache du navigateur (Ctrl+Shift+R)")
            self.stdout.write("  2. Vérifiez que le fichier a bien été modifié")
            self.stdout.write("  3. Vérifiez les logs Django pour d'éventuelles erreurs")
        else:
            self.stdout.write(self.style.ERROR("✗ Échec de l'application du filigrane"))
            self.stdout.write("Vérifiez les logs Django pour plus de détails")

