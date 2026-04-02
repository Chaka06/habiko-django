import logging

from django.core.management.base import BaseCommand

from ads.models import AdMedia


logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = "Génère des miniatures (thumbnails) optimisées pour toutes les photos d'annonces."

    def add_arguments(self, parser):
        parser.add_argument(
            "--force",
            action="store_true",
            help="Regénérer les miniatures même si elles existent déjà.",
        )

    def handle(self, *args, **options):
        force = options["force"]

        qs = AdMedia.objects.all()
        if not force:
            qs = qs.filter(thumbnail__isnull=True)

        total = qs.count()
        if total == 0:
            self.stdout.write(self.style.SUCCESS("Aucune miniature à générer."))
            return

        self.stdout.write(
            self.style.NOTICE(
                f"Génération des miniatures pour {total} média(s) d'annonces (force={force})..."
            )
        )

        processed = 0
        errors = 0

        for media in qs.iterator():
            try:
                # Utilise la logique existante (filigrane + thumbnail)
                ok = media._add_watermark_and_thumbnail()
                if ok:
                    media.save(update_fields=["thumbnail"])
                    processed += 1
                else:
                    errors += 1
                    logger.warning("Impossible de générer la miniature pour AdMedia id=%s", media.id)
            except Exception as e:
                errors += 1
                logger.exception("Erreur lors de la génération de miniature pour AdMedia id=%s: %s", media.id, e)

        self.stdout.write(
            self.style.SUCCESS(
                f"Miniatures générées: {processed} / {total} (erreurs: {errors})."
            )
        )

