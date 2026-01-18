"""
Commande pour mettre à jour l'image de fête dans le header
Change automatiquement l'image selon la date :
- Avant le 1er janvier 2026 : champagne.png
- À partir du 1er janvier 2026 : newyear2026.png
"""
import os
from django.core.management.base import BaseCommand
from django.conf import settings
from django.utils import timezone
from datetime import date


class Command(BaseCommand):
    help = "Met à jour l'image de fête dans le header selon la date"

    def handle(self, *args, **options):
        # Date de transition : 1er janvier 2026
        transition_date = date(2026, 1, 1)
        today = timezone.now().date()
        
        # Déterminer quelle image utiliser
        if today >= transition_date:
            image_name = "newyear2026.png"
            image_display = "Happy New Year 2026"
        else:
            image_name = "champagne.png"
            image_display = "Champagne"
        
        # Vérifier que l'image existe
        static_dir = None
        if hasattr(settings, 'STATICFILES_DIRS') and settings.STATICFILES_DIRS:
            static_dir = settings.STATICFILES_DIRS[0]
        else:
            static_dir = os.path.join(settings.BASE_DIR, 'static')
        
        image_path = os.path.join(str(static_dir), 'img', image_name)
        
        if not os.path.exists(image_path):
            self.stdout.write(
                self.style.ERROR(f"✗ Image introuvable: {image_path}")
            )
            return
        
        self.stdout.write(f"Date actuelle: {today}")
        self.stdout.write(f"Date de transition: {transition_date}")
        self.stdout.write(f"Image sélectionnée: {image_display} ({image_name})")
        self.stdout.write(f"Chemin: {image_path}")
        self.stdout.write(
            self.style.SUCCESS(f"✓ L'image {image_display} sera utilisée dans le header")
        )
        
        # Note: Le template base.html utilise déjà une logique conditionnelle
        # Cette commande sert principalement à vérifier et informer

