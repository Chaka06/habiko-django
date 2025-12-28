from django.core.management.base import BaseCommand
from ads.models import City
from django.utils.text import slugify


CITIES = [
    ("Abidjan", "Lagunes"),
    ("Bouaké", "Vallée du Bandama"),
    ("Daloa", "Sassandra-Marahoué"),
    ("San Pedro", "Bas-Sassandra"),
    ("Yamoussoukro", "Lacs"),
    ("Korhogo", "Savanes"),
    ("Man", "Montagnes"),
    ("Divo", "Lôh-Djiboua"),
    ("Abengourou", "Indénié-Djuablin"),
    ("Gagnoa", "Gôh"),
    ("Soubré", "Nawa"),
    ("Anyama", "Lagunes"),
    ("Agboville", "Agnéby-Tiassa"),
    ("Dimbokro", "N'Zi"),
    ("Bondoukou", "Gontougo"),
    ("Odienné", "Kabadougou"),
]


class Command(BaseCommand):
    help = "Seed principales villes de Côte d’Ivoire"

    def handle(self, *args, **options):
        created = 0
        for name, region in CITIES:
            slug = slugify(name)
            obj, was_created = City.objects.get_or_create(
                slug=slug, defaults={"name": name.strip(), "region": region}
            )
            if was_created:
                created += 1
        self.stdout.write(
            self.style.SUCCESS(
                f"Villes seedées: {created} créées, {len(CITIES)-created} existantes."
            )
        )
