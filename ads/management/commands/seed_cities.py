from django.core.management.base import BaseCommand

from ads.models import City


DEFAULT_CITIES = [
    # Principales villes de Côte d'Ivoire
    ("Abidjan", "District Autonome d'Abidjan"),
    ("Yamoussoukro", "District Autonome de Yamoussoukro"),
    ("Bouaké", "Région de Gbêkê"),
    ("Daloa", "Région du Haut-Sassandra"),
    ("San-Pédro", "Région de San-Pédro"),
    ("Korhogo", "Région du Poro"),
    ("Man", "Région du Tonkpi"),
    ("Gagnoa", "Région du Gôh"),
    ("Abengourou", "Région de l'Indénié-Djuablin"),
    ("Divo", "Région du Lôh-Djiboua"),
    ("Anyama", "District Autonome d'Abidjan"),
    ("Yopougon", "District Autonome d'Abidjan"),
    ("Cocody", "District Autonome d'Abidjan"),
    ("Marcory", "District Autonome d'Abidjan"),
    ("Treichville", "District Autonome d'Abidjan"),
    ("Plateau", "District Autonome d'Abidjan"),
    ("Koumassi", "District Autonome d'Abidjan"),
    ("Port-Bouët", "District Autonome d'Abidjan"),
    ("Bingerville", "District Autonome d'Abidjan"),
]


class Command(BaseCommand):
    help = "Crée les villes de base pour KIABA Rencontres (Côte d'Ivoire) si elles n'existent pas."

    def handle(self, *args, **options):
        created_count = 0
        for name, region in DEFAULT_CITIES:
            city, created = City.objects.get_or_create(
                name=name,
                defaults={"region": region},
            )
            if created:
                created_count += 1
                self.stdout.write(self.style.SUCCESS(f"Ville créée : {city.name}"))
            else:
                # Mettre à jour la région si nécessaire
                if city.region != region:
                    city.region = region
                    city.save(update_fields=["region"])
                    self.stdout.write(
                        self.style.WARNING(
                            f"Ville mise à jour : {city.name} (région: {region})"
                        )
                    )

        if created_count == 0:
            self.stdout.write(
                self.style.WARNING("Aucune nouvelle ville créée (elles existent déjà).")
            )
        else:
            self.stdout.write(
                self.style.SUCCESS(f"{created_count} ville(s) créée(s) avec succès.")
            )

