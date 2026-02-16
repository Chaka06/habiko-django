from django.db import models, transaction
from django.utils.text import slugify
from django.utils import timezone
from django.conf import settings
from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _
from PIL import Image, ImageEnhance
import logging
import os
from io import BytesIO
from django.core.files.base import ContentFile

logger = logging.getLogger(__name__)


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
        ESCORTE_GIRL = "escorte_girl", "Escorte girl"
        ESCORTE_BOY = "escorte_boy", "Escorte boy"
        TRANSGENRE = "transgenre", "Transgenre"

    class Status(models.TextChoices):
        DRAFT = "draft", "Draft"
        PENDING = "pending", "Pending"
        APPROVED = "approved", "Approved"
        REJECTED = "rejected", "Rejected"
        ARCHIVED = "archived", "Archived"

    # Sous-catégories communes aux annonces adultes / escortes
    SUBCATEGORY_CHOICES = [
        "Sex vaginal",
        "Sex anal (sodomie)",
        "Massage sexuel",
        "Massage du corps",
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
        help_text=_("Données supplémentaires selon la catégorie (prix, surface, etc.)"),
    )
    expires_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    # Champs pour les boosts
    is_premium = models.BooleanField(
        default=False, help_text=_("Annonce premium (en tête de liste)")
    )
    premium_until = models.DateTimeField(
        null=True, blank=True, help_text=_("Date jusqu'à laquelle l'annonce est premium")
    )
    is_urgent = models.BooleanField(default=False, help_text=_("Annonce urgente (logo urgent)"))
    urgent_until = models.DateTimeField(
        null=True, blank=True, help_text=_("Date jusqu'à laquelle l'annonce est urgente")
    )
    extended_until = models.DateTimeField(
        null=True, blank=True, help_text=_("Date de prolongation de l'annonce")
    )

    features = models.ManyToManyField(Feature, through="AdFeature", blank=True)

    # False tant que le traitement async (filigrane + miniature) des photos n'est pas terminé
    image_processing_done = models.BooleanField(
        default=True,
        help_text=_("True une fois toutes les images traitées (filigrane + miniature). Les annonces n'apparaissent en liste qu'une fois True."),
    )

    class Meta:
        ordering = ["-is_premium", "-is_urgent", "-created_at"]
        indexes = [
            models.Index(
                fields=["status", "is_premium", "is_urgent", "created_at"], name="ad_list_idx"
            ),
            models.Index(
                fields=["status", "image_processing_done"], name="ad_list_ready_idx"
            ),
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
    # Miniature optimisée pour les listes / aperçus (beaucoup plus légère que l'originale)
    thumbnail = models.ImageField(upload_to="ads/thumbnails/", blank=True, null=True)
    is_primary = models.BooleanField(default=False)
    _watermark_applied = False  # Flag pour éviter de réappliquer le filigrane

    def clean(self):
        # Enforce max 5 media per Ad
        existing = (
            AdMedia.objects.filter(ad=self.ad).exclude(pk=self.pk).count() if self.ad_id else 0
        )
        if existing >= 5:
            raise ValidationError("Maximum 5 photos per ad.")

    def _add_watermark_and_thumbnail(self):
        """
        Ajoute le filigrane du logo au centre de l'image
        + génère une miniature optimisée (thumbnail) pour les listes.
        """
        if not self.image or self._watermark_applied:
            return False

        import logging

        logger = logging.getLogger(__name__)

        try:
            # Déterminer le chemin de l'image (jamais utiliser .path avec S3/Supabase — lève "doesn't support absolute paths")
            image_path = None
            original_format = None
            img = None

            try:
                if hasattr(self.image, "path"):
                    _path = self.image.path
                    if _path and os.path.exists(_path):
                        image_path = _path
                        img = Image.open(image_path)
                        original_format = img.format
            except (NotImplementedError, ValueError, OSError):
                # Stockage distant (S3/Supabase) : pas de .path
                pass

            if img is None and image_path is None and hasattr(self.image, "file") and hasattr(self.image.file, "read"):
                # Fichier en mémoire (nouveau upload)
                self.image.file.seek(0)
                img = Image.open(self.image.file)
                original_format = img.format
            elif img is None and image_path is None and self.image.name:
                # Ouvrir depuis le storage (S3/Supabase)
                with self.image.open("rb") as f:
                    img = Image.open(f)
                    img.load()
                original_format = img.format

            if img is None:
                logger.warning("Impossible d'ouvrir l'image, abandon filigrane/thumbnail: %s", self.image.name)
                return False
            if not original_format:
                ext = os.path.splitext(self.image.name or "")[1].lower()
                format_map = {".jpg": "JPEG", ".jpeg": "JPEG", ".png": "PNG", ".webp": "WEBP"}
                original_format = format_map.get(ext, "JPEG")

            # OPTIMISATION : Redimensionner pour alléger (max 1000px, qualité réduite plus bas)
            MAX_WIDTH = 1000
            MAX_HEIGHT = 1000
            img_width, img_height = img.size

            if img_width > MAX_WIDTH or img_height > MAX_HEIGHT:
                ratio = min(MAX_WIDTH / img_width, MAX_HEIGHT / img_height)
                new_width = int(img_width * ratio)
                new_height = int(img_height * ratio)
                img = img.resize((new_width, new_height), Image.Resampling.LANCZOS)
                logger.info(
                    f"Image redimensionnée de {img_width}x{img_height} à {new_width}x{new_height}"
                )

            # Convertir en RGBA pour le traitement
            if img.mode != "RGBA":
                img = img.convert("RGBA")

            # Chercher le logo dans STATICFILES_DIRS
            logo_path = None
            if hasattr(settings, "STATICFILES_DIRS") and settings.STATICFILES_DIRS:
                for static_dir in settings.STATICFILES_DIRS:
                    potential_path = os.path.join(str(static_dir), "img", "logo.png")
                    if os.path.exists(potential_path):
                        logo_path = potential_path
                        break

            # Si pas trouvé, essayer le chemin par défaut
            if not logo_path:
                logo_path = os.path.join(settings.BASE_DIR, "static", "img", "logo.png")

            if not os.path.exists(logo_path):
                # Si le logo n'existe pas, on ne fait rien, mais on peut tout de même générer un thumbnail
                logger.warning(
                    "Logo pour filigrane introuvable, génération seulement du thumbnail."
                )

            # Si le logo existe, appliquer le filigrane
            if os.path.exists(logo_path):
                logo = Image.open(logo_path)
                if logo.mode != "RGBA":
                    logo = logo.convert("RGBA")

                # Taille du logo (25 % de la plus petite dimension)
                img_width, img_height = img.size
                min_dimension = min(img_width, img_height)
                logo_size = int(min_dimension * 0.25)

                logo_ratio = logo.width / logo.height
                if logo.width > logo.height:
                    new_logo_width = logo_size
                    new_logo_height = int(logo_size / logo_ratio)
                else:
                    new_logo_height = logo_size
                    new_logo_width = int(logo_size * logo_ratio)

                logo = logo.resize((new_logo_width, new_logo_height), Image.Resampling.LANCZOS)

                # Opacité 50 % : réduire le canal alpha
                r, g, b, a = logo.split()
                a = a.point(lambda x: int(x * 0.5))
                logo = Image.merge("RGBA", (r, g, b, a))

                # Position au centre
                x = (img_width - new_logo_width) // 2
                y = (img_height - new_logo_height) // 2

                img.paste(logo, (x, y), logo)

            # Sauvegarder l'image principale optimisée (WebP si possible)
            output = BytesIO()
            format_map = {
                "JPEG": "JPEG",
                "PNG": "PNG",
                "WEBP": "WEBP",
            }
            img_format = format_map.get(original_format or img.format, "JPEG")

            try:
                # Convertir en RGB pour WebP/JPEG
                if img.mode == "RGBA":
                    rgb_img = Image.new("RGB", img.size, (255, 255, 255))
                    rgb_img.paste(img, mask=img.split()[3])
                    img_rgb = rgb_img
                else:
                    img_rgb = img

                img_rgb.save(
                    output,
                    format="WEBP",
                    quality=65,
                    method=6,
                    optimize=True,
                )
                img_format = "WEBP"
                logger.info("Image sauvegardée en WebP (compressée)")
            except Exception as e:
                logger.warning(f"WebP non disponible, utilisation du format {img_format}: {str(e)}")
                if img_format == "PNG":
                    if img.mode != "RGBA":
                        img = img.convert("RGBA")
                    img.save(output, format="PNG", optimize=True, compress_level=9)
                else:
                    if img.mode == "RGBA":
                        rgb_img = Image.new("RGB", img.size, (255, 255, 255))
                        rgb_img.paste(img, mask=img.split()[3])
                        img = rgb_img
                    img.save(output, format="JPEG", quality=65, optimize=True, progressive=True)

            output.seek(0)
            image_content = output.read()

            # Toujours enregistrer l'image optimisée dans le storage (dossier local ou S3/Supabase)
            # pour que le lien en base pointe vers le fichier allégé et qu'il ne se perde pas au déploiement.
            base_name = os.path.splitext(self.image.name)[0]
            if not base_name.strip():
                base_name = "image"
            optimized_name = f"{base_name}.webp"
            if image_path and os.path.exists(image_path):
                with open(image_path, "wb") as f:
                    f.write(image_content)
                logger.info(f"Filigrane appliqué et sauvegardé: {image_path}")
            else:
                # Upload en mémoire ou stockage distant : sauver l'image optimisée dans le storage
                # Supabase n'accepte pas application/octet-stream → préciser image/webp
                main_file = ContentFile(image_content)
                main_file.content_type = "image/webp"
                self.image.save(optimized_name, main_file, save=False)
                logger.info("Image optimisée enregistrée dans le storage: %s", optimized_name)

            output.close()

            # Générer la miniature (toujours depuis l'image en mémoire — pas de .path avec S3/Supabase)
            thumb_img = (img.convert("RGB") if img.mode != "RGB" else img.copy())

            THUMBNAIL_SIZE = (320, 320)
            thumb_img.thumbnail(THUMBNAIL_SIZE, Image.Resampling.LANCZOS)

            thumb_output = BytesIO()
            thumb_img.save(
                thumb_output,
                format="WEBP",
                quality=65,
                method=6,
                optimize=True,
            )
            thumb_output.seek(0)

            thumb_name = os.path.splitext(self.image.name)[0] + "_thumb.webp"
            thumb_file = ContentFile(thumb_output.read())
            thumb_file.content_type = "image/webp"
            self.thumbnail.save(thumb_name, thumb_file, save=False)
            thumb_output.close()

            self._watermark_applied = True
            return True

        except Exception as e:
            import logging

            logger = logging.getLogger(__name__)
            logger.warning(f"Erreur lors de l'ajout du filigrane / thumbnail: {str(e)}")
            return False

    def save(self, *args, **kwargs):
        with transaction.atomic():
            try:
                self.full_clean()
            except ValidationError:
                # Ne pas bloquer la sauvegarde (ex. stockage S3 sans .path) — l'image sera tout de même enregistrée
                logger.warning(
                    "AdMedia full_clean ignoré (image enregistrée sans validation stricte): %s",
                    self.image.name if self.image else "sans nom",
                )

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

            # Sauvegarder d'abord pour obtenir le chemin du fichier (upload brut = réponse rapide)
            super().save(*args, **kwargs)

            # Filigrane + miniature : en async (Celery) pour ne pas bloquer le dépôt d'annonce (15s → <2s)
            if image_changed and self.image:
                if getattr(settings, "USE_ASYNC_IMAGE_PROCESSING", True):
                    from ads.tasks import process_ad_media_image
                    transaction.on_commit(lambda: process_ad_media_image.delay(self.pk))
                else:
                    try:
                        processed = self._add_watermark_and_thumbnail()
                        if processed:
                            self.save(update_fields=["image", "thumbnail"])
                    except Exception as e:
                        logger.warning("Filigrane/thumbnail non appliqué (image tout de même enregistrée): %s", e)

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
