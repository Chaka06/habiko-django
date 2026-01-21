from django.db import models, transaction
from django.utils.text import slugify
from django.utils import timezone
from django.conf import settings
from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _
from PIL import Image, ImageEnhance
import os
from io import BytesIO
from django.core.files.base import ContentFile


class City(models.Model):
    name = models.CharField(max_length=120, unique=True)
    slug = models.SlugField(max_length=140, unique=True)
    region = models.CharField(max_length=120, blank=True, default="")

    class Meta:
        ordering = ["name"]
        verbose_name = _("Ville")
        verbose_name_plural = _("Villes")

    def save(self, *args, **kwargs):  # pragma: no cover
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)

    def __str__(self) -> str:  # pragma: no cover
        return self.name


class Feature(models.Model):
    name = models.CharField(max_length=64, unique=True)

    class Meta:
        ordering = ["name"]

    def __str__(self) -> str:  # pragma: no cover
        return self.name


class Ad(models.Model):
    class Category(models.TextChoices):
        MAISONS_APPARTEMENTS = "maisons_appartements", "Maisons et Appartements"
        VILLAS_RESIDENCES = "villas_residences", "Villas et Résidences"
        TERRAINS = "terrains", "Terrains"
        LOCATIONS = "locations", "Locations"

    class Status(models.TextChoices):
        DRAFT = "draft", "Draft"
        PENDING = "pending", "Pending"
        APPROVED = "approved", "Approved"
        REJECTED = "rejected", "Rejected"
        ARCHIVED = "archived", "Archived"

    SUBCATEGORY_CHOICES = [
        # Maisons et Appartements
        "Maison à vendre",
        "Appartement à vendre",
        "Studio à vendre",
        "Duplex à vendre",
        "Villa à vendre",
        "Maison meublée à vendre",
        "Appartement meublé à vendre",
        # Villas et Résidences
        "Villa de luxe",
        "Résidence meublée",
        "Résidence de standing",
        "Villa avec piscine",
        "Résidence sécurisée",
        # Terrains
        "Terrain à vendre",
        "Terrain constructible",
        "Terrain viabilisé",
        "Parcelle à vendre",
        "Terrain commercial",
        # Locations
        "Maison à louer",
        "Appartement à louer",
        "Studio à louer",
        "Villa à louer",
        "Résidence meublée à louer",
    ]

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    title = models.CharField(max_length=140)
    description_sanitized = models.TextField()
    category = models.CharField(max_length=20, choices=Category.choices)
    subcategories = models.JSONField(default=list)
    city = models.ForeignKey(City, on_delete=models.PROTECT)
    area = models.CharField(max_length=120, blank=True, default="")
    is_verified = models.BooleanField(default=False)
    status = models.CharField(max_length=10, choices=Status.choices, default=Status.DRAFT)
    slug = models.SlugField(max_length=180, unique=True)
    views_count = models.PositiveIntegerField(default=0)
    contacts_clicks = models.JSONField(default=dict)
    additional_data = models.JSONField(
        default=dict,
        help_text=_("Données supplémentaires selon la catégorie (prix, surface, etc.)")
    )
    expires_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    # Champs pour les boosts
    is_premium = models.BooleanField(
        default=False,
        help_text=_("Annonce premium (en tête de liste)")
    )
    premium_until = models.DateTimeField(
        null=True,
        blank=True,
        help_text=_("Date jusqu'à laquelle l'annonce est premium")
    )
    is_urgent = models.BooleanField(
        default=False,
        help_text=_("Annonce urgente (logo urgent)")
    )
    urgent_until = models.DateTimeField(
        null=True,
        blank=True,
        help_text=_("Date jusqu'à laquelle l'annonce est urgente")
    )
    extended_until = models.DateTimeField(
        null=True,
        blank=True,
        help_text=_("Date de prolongation de l'annonce")
    )

    features = models.ManyToManyField(Feature, through="AdFeature", blank=True)

    class Meta:
        ordering = ["-is_premium", "-is_urgent", "-created_at"]
        indexes = [
            models.Index(fields=["status", "is_premium", "is_urgent", "created_at"], name="ad_list_idx"),
            models.Index(fields=["status", "category"], name="ad_category_idx"),
            models.Index(fields=["status", "city"], name="ad_city_idx"),
            models.Index(fields=["slug"], name="ad_slug_idx"),
            models.Index(fields=["user", "status"], name="ad_user_status_idx"),
        ]

    def clean(self):
        invalid = [s for s in self.subcategories if s not in self.SUBCATEGORY_CHOICES]
        if invalid:
            raise ValidationError({"subcategories": f"Invalid subcategories: {invalid}"})

    def save(self, *args, **kwargs):
        if not self.slug:
            base = slugify(self.title)[:150]
            candidate = base
            idx = 1
            while Ad.objects.filter(slug=candidate).exclude(pk=self.pk).exists():
                idx += 1
                candidate = f"{base}-{idx}"
            self.slug = candidate
        # Initialize contacts_clicks structure
        if not self.contacts_clicks:
            self.contacts_clicks = {"sms": 0, "whatsapp": 0, "call": 0}
        # Set default expiration to 14 days if not set
        if not self.expires_at:
            self.expires_at = timezone.now() + timezone.timedelta(days=14)
        super().save(*args, **kwargs)

    def __str__(self) -> str:  # pragma: no cover
        return self.title

    def get_subcategories_display(self):
        """Retourne les sous-catégories sous forme de chaîne lisible"""
        if not self.subcategories:
            return "Aucune"
        return ", ".join(self.subcategories)

    get_subcategories_display.short_description = "Sous-catégories"


class AdMedia(models.Model):
    ad = models.ForeignKey(Ad, on_delete=models.CASCADE, related_name="media")
    image = models.ImageField(upload_to="ads/")
    is_primary = models.BooleanField(default=False)
    _watermark_applied = False  # Flag pour éviter de réappliquer le filigrane

    def clean(self):
        # Enforce max 5 media per Ad
        existing = (
            AdMedia.objects.filter(ad=self.ad).exclude(pk=self.pk).count() if self.ad_id else 0
        )
        if existing >= 5:
            raise ValidationError("Maximum 5 photos per ad.")

    def _add_watermark(self):
        """Ajoute le filigrane du logo au centre de l'image"""
        if not self.image or self._watermark_applied:
            return False
        
        import logging
        logger = logging.getLogger(__name__)
        
        try:
            # Déterminer le chemin de l'image
            image_path = None
            original_format = None
            
            if hasattr(self.image, 'path') and os.path.exists(self.image.path):
                # Fichier sur le disque (image existante)
                image_path = self.image.path
                img = Image.open(image_path)
                original_format = img.format
                # Si le format n'est pas détecté, essayer depuis l'extension
                if not original_format:
                    ext = os.path.splitext(image_path)[1].lower()
                    format_map = {'.jpg': 'JPEG', '.jpeg': 'JPEG', '.png': 'PNG', '.webp': 'WEBP'}
                    original_format = format_map.get(ext, 'JPEG')
            elif hasattr(self.image, 'file') and hasattr(self.image.file, 'read'):
                # Fichier en mémoire (nouveau upload)
                self.image.file.seek(0)
                img = Image.open(self.image.file)
                original_format = img.format
            else:
                logger.warning(f"Impossible d'ouvrir l'image: {self.image.name if self.image else 'None'}")
                return False
            
            # Convertir en RGBA si nécessaire
            if img.mode != 'RGBA':
                img = img.convert('RGBA')
            
            # Chercher le logo dans STATICFILES_DIRS
            logo_path = None
            if hasattr(settings, 'STATICFILES_DIRS') and settings.STATICFILES_DIRS:
                for static_dir in settings.STATICFILES_DIRS:
                    potential_path = os.path.join(str(static_dir), 'img', 'logo.png')
                    if os.path.exists(potential_path):
                        logo_path = potential_path
                        break
            
            # Si pas trouvé, essayer le chemin par défaut
            if not logo_path:
                logo_path = os.path.join(settings.BASE_DIR, 'static', 'img', 'logo.png')
            
            if not os.path.exists(logo_path):
                # Si le logo n'existe pas, on ne fait rien
                return False
            
            # Ouvrir le logo
            logo = Image.open(logo_path)
            # Convertir le logo en RGBA si nécessaire
            if logo.mode != 'RGBA':
                logo = logo.convert('RGBA')
            
            # Calculer la taille du logo (50% de la plus petite dimension de l'image)
            img_width, img_height = img.size
            min_dimension = min(img_width, img_height)
            logo_size = int(min_dimension * 0.5)
            
            # Redimensionner le logo en gardant les proportions
            logo_ratio = logo.width / logo.height
            if logo.width > logo.height:
                new_logo_width = logo_size
                new_logo_height = int(logo_size / logo_ratio)
            else:
                new_logo_height = logo_size
                new_logo_width = int(logo_size * logo_ratio)
            
            logo = logo.resize((new_logo_width, new_logo_height), Image.Resampling.LANCZOS)
            
            # Calculer la position du logo au centre
            x = (img_width - new_logo_width) // 2
            y = (img_height - new_logo_height) // 2
            
            # Coller le logo sur l'image (100% opaque, pas de transparence)
            img.paste(logo, (x, y), logo)
            
            # Sauvegarder l'image modifiée
            output = BytesIO()
            # Conserver le format original
            format_map = {
                'JPEG': 'JPEG',
                'PNG': 'PNG',
                'WEBP': 'WEBP',
            }
            # Utiliser le format original détecté ou celui de l'image
            img_format = format_map.get(original_format or img.format, 'JPEG')
            
            if img_format == 'PNG':
                img.save(output, format='PNG', quality=95)
            else:
                # Convertir en RGB pour JPEG
                if img.mode == 'RGBA':
                    rgb_img = Image.new('RGB', img.size, (255, 255, 255))
                    rgb_img.paste(img, mask=img.split()[3])
                    img = rgb_img
                img.save(output, format=img_format, quality=85, optimize=True)
            
            output.seek(0)
            
            # Remplacer le fichier image
            output.seek(0)
            image_content = output.read()
            
            if image_path and os.path.exists(image_path):
                # Fichier existant sur le disque - écrire directement
                with open(image_path, 'wb') as f:
                    f.write(image_content)
                logger.info(f"Filigrane appliqué et sauvegardé: {image_path}")
            elif hasattr(self.image, 'file') and hasattr(self.image.file, 'read'):
                # Nouveau fichier uploadé (en mémoire)
                self.image.file.seek(0)
                self.image.file = ContentFile(image_content)
            else:
                # Utiliser la méthode save de Django
                self.image.save(
                    self.image.name,
                    ContentFile(image_content),
                    save=False
                )
            
            output.close()
            self._watermark_applied = True
            return True
            
        except Exception as e:
            # En cas d'erreur, on continue sans filigrane
            import logging
            logger = logging.getLogger(__name__)
            logger.warning(f"Erreur lors de l'ajout du filigrane: {str(e)}")
            return False

    def save(self, *args, **kwargs):
        with transaction.atomic():
            self.full_clean()
            
            # Vérifier si c'est une nouvelle image ou si l'image a changé
            is_new = self.pk is None
            image_changed = False
            
            if not is_new:
                try:
                    old_instance = AdMedia.objects.get(pk=self.pk)
                    # Comparer les noms de fichiers pour détecter un changement
                    old_image_name = old_instance.image.name if old_instance.image else None
                    new_image_name = self.image.name if self.image else None
                    image_changed = old_image_name != new_image_name
                except AdMedia.DoesNotExist:
                    image_changed = True
            else:
                # Nouvelle instance, l'image sera traitée
                image_changed = bool(self.image)
            
            # Sauvegarder d'abord pour obtenir le chemin du fichier
            super().save(*args, **kwargs)
            
            # Appliquer le filigrane après la sauvegarde pour les images existantes
            # (pour avoir accès au chemin du fichier sur le disque)
            if image_changed and self.image:
                watermark_applied = self._add_watermark()
                # Si le filigrane a été appliqué et qu'on a écrit directement sur le disque,
                # on doit rafraîchir l'instance pour que Django reconnaisse le changement
                if watermark_applied:
                    # Rafraîchir depuis la base de données
                    self.refresh_from_db()
            
            # Ensure only one primary
            if self.is_primary:
                AdMedia.objects.filter(ad=self.ad).exclude(pk=self.pk).update(is_primary=False)

    def __str__(self) -> str:  # pragma: no cover
        return f"Media({self.ad_id})"


class Availability(models.Model):
    ad = models.OneToOneField(Ad, on_delete=models.CASCADE, related_name="availability")
    days_of_week = models.JSONField(default=list)
    time_ranges = models.JSONField(default=list)  # e.g., [{"start":"09:00","end":"18:00"}]
    on_request = models.BooleanField(default=False)

    def __str__(self) -> str:  # pragma: no cover
        return f"Availability({self.ad_id})"


class AdFeature(models.Model):
    ad = models.ForeignKey(Ad, on_delete=models.CASCADE)
    feature = models.ForeignKey(Feature, on_delete=models.CASCADE)

    class Meta:
        unique_together = ("ad", "feature")


class Report(models.Model):
    ad = models.ForeignKey(Ad, on_delete=models.CASCADE)
    reporter_fingerprint = models.CharField(max_length=128)
    reason = models.TextField()
    status = models.CharField(max_length=20, default="pending")
    created_at = models.DateTimeField(auto_now_add=True)


class AuditLog(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL
    )
    action = models.CharField(max_length=64)
    entity_type = models.CharField(max_length=64)
    entity_id = models.CharField(max_length=64)
    metadata = models.JSONField(default=dict)
    created_at = models.DateTimeField(default=timezone.now)


# Create your models here.
