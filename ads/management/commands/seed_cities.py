from django.core.management.base import BaseCommand

from ads.models import City


# Communes et quartiers d'Abidjan (District Autonome d'Abidjan)
ABIDJAN_COMMUNES = [
    ("Abobo", "District Autonome d'Abidjan"),
    ("Adjamé", "District Autonome d'Abidjan"),
    ("Angré", "District Autonome d'Abidjan"),
    ("Anono", "District Autonome d'Abidjan"),
    ("Anani", "District Autonome d'Abidjan"),
    ("Attécoubé", "District Autonome d'Abidjan"),
    ("Bingerville", "District Autonome d'Abidjan"),
    ("Blockhaus", "District Autonome d'Abidjan"),
    ("Cocody", "District Autonome d'Abidjan"),
    ("Djorobité", "District Autonome d'Abidjan"),
    ("Faya", "District Autonome d'Abidjan"),
    ("Gonzague", "District Autonome d'Abidjan"),
    ("Koumassi", "District Autonome d'Abidjan"),
    ("Mbadon", "District Autonome d'Abidjan"),
    ("Marcory", "District Autonome d'Abidjan"),
    ("Mpouto", "District Autonome d'Abidjan"),
    ("Palmeraie", "District Autonome d'Abidjan"),
    ("Plateau", "District Autonome d'Abidjan"),
    ("Port-Bouët", "District Autonome d'Abidjan"),
    ("Treichville", "District Autonome d'Abidjan"),
    ("Yopougon", "District Autonome d'Abidjan"),
    ("Anyama", "District Autonome d'Abidjan"),
]

# Villes de l'intérieur et autres
INTERIOR_CITIES = [
    ("Abidjan", "Lagunes"),
    ("Abengourou", "Indénié-Djuablin"),
    ("Bouaké", "Vallée du Bandama"),
    ("Daloa", "Haut-Sassandra"),
    ("Issia", "Haut-Sassandra"),
    ("Korhogo", "Poro"),
    ("Man", "Tonkpi"),
    ("San-Pédro", "Bas-Sassandra"),
    ("Yamoussoukro", "District de Yamoussoukro"),
    ("Gagnoa", "Gôh"),
    ("Divo", "Lôh-Djiboua"),
    ("Soubré", "Nawa"),
    ("Bondoukou", "Gontougo"),
    ("Odienné", "Kabadougou"),
    ("Adzopé", "La Mé"),
    ("Dabou", "Grands-Ponts"),
    ("Sinfra", "Marahoué"),
    ("Katiola", "Hambol"),
    ("Dimbokro", "N'Zi"),
]

DEFAULT_CITIES = ABIDJAN_COMMUNES + INTERIOR_CITIES


class Command(BaseCommand):
    help = "Crée les villes et communes de base pour KIABA Rencontres (Côte d'Ivoire) si elles n'existent pas."

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
