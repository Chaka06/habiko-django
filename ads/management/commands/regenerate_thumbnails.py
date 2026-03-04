"""
Régénère les miniatures (thumbnails) de toutes les images existantes
avec les paramètres de compression actuels (quality=50, 320x320).

Usage:
    python manage.py regenerate_thumbnails
    python manage.py regenerate_thumbnails --limit 50
    python manage.py regenerate_thumbnails --dry-run
"""
from io import BytesIO

from django.core.files.base import ContentFile
from django.core.management.base import BaseCommand

from ads.models import AdMedia
from PIL import Image


class Command(BaseCommand):
    help = "Régénère les thumbnails avec la compression optimisée (quality=50)"

    def add_arguments(self, parser):
        parser.add_argument("--dry-run", action="store_true")
        parser.add_argument("--limit", type=int, default=None)

    def handle(self, *args, **options):
        dry_run = options["dry_run"]
        limit = options["limit"]

        qs = AdMedia.objects.filter(image__isnull=False).exclude(image="")
        if limit:
            qs = qs[:limit]

        total = qs.count()
        self.stdout.write(f"Régénération des thumbnails pour {total} image(s)...")

        processed = errors = 0

        for media in qs:
            try:
                # Ouvrir l'image existante (watermarkée) depuis le storage
                img = None
                try:
                    if hasattr(media.image, "path"):
                        import os
                        if os.path.exists(media.image.path):
                            img = Image.open(media.image.path)
                            img.load()
                except (NotImplementedError, ValueError, OSError):
                    pass

                if img is None:
                    with media.image.open("rb") as f:
                        img = Image.open(f)
                        img.load()

                if dry_run:
                    self.stdout.write(f"  [DRY-RUN] {media.image.name} (Ad #{media.ad_id})")
                    processed += 1
                    continue

                # Générer thumbnail 320x320 quality=50
                thumb = img.convert("RGB") if img.mode != "RGB" else img.copy()
                thumb.thumbnail((320, 320), Image.Resampling.LANCZOS)

                buf = BytesIO()
                thumb.save(buf, format="WEBP", quality=50, method=6, optimize=True)
                buf.seek(0)

                import os
                thumb_name = os.path.splitext(media.image.name)[0] + "_thumb.webp"
                thumb_file = ContentFile(buf.read())
                thumb_file.content_type = "image/webp"
                media.thumbnail.save(thumb_name, thumb_file, save=False)
                media.save(update_fields=["thumbnail"])
                buf.close()

                processed += 1
                self.stdout.write(self.style.SUCCESS(f"  ✓ {media.image.name}"))

            except Exception as e:
                errors += 1
                self.stdout.write(self.style.ERROR(f"  ✗ {media.image.name if media.image else '?'}: {e}"))

        verb = "[DRY-RUN]" if dry_run else "✓"
        self.stdout.write(self.style.SUCCESS(f"\n{verb} {processed}/{total} thumbnail(s) traité(s)"))
        if errors:
            self.stdout.write(self.style.WARNING(f"⚠ {errors} erreur(s)"))
