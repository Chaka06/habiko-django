from django.core.management.base import BaseCommand
from ads.models import City


class Command(BaseCommand):
    help = "Add all major cities of Côte d'Ivoire"

    def handle(self, *args, **options):
        cities_data = [
            # Grandes villes
            {"name": "Abidjan", "region": "Lagunes"},
            {"name": "Bouaké", "region": "Vallée du Bandama"},
            {"name": "Daloa", "region": "Haut-Sassandra"},
            {"name": "San-Pédro", "region": "Bas-Sassandra"},
            {"name": "Yamoussoukro", "region": "Yamoussoukro"},
            {"name": "Korhogo", "region": "Poro"},
            {"name": "Man", "region": "Tonkpi"},
            {"name": "Gagnoa", "region": "Gôh"},
            {"name": "Abengourou", "region": "Indénié-Djuablin"},
            {"name": "Anyama", "region": "Lagunes"},
            # Autres villes importantes
            {"name": "Bingerville", "region": "Lagunes"},
            {"name": "Cocody", "region": "Lagunes"},
            {"name": "Marcory", "region": "Lagunes"},
            {"name": "Port-Bouët", "region": "Lagunes"},
            {"name": "Treichville", "region": "Lagunes"},
            {"name": "Adjamé", "region": "Lagunes"},
            {"name": "Attécoubé", "region": "Lagunes"},
            {"name": "Koumassi", "region": "Lagunes"},
            {"name": "Plateau", "region": "Lagunes"},
            {"name": "Yopougon", "region": "Lagunes"},
            # Villes du centre
            {"name": "Divo", "region": "Lôh-Djiboua"},
            {"name": "Lakota", "region": "Lôh-Djiboua"},
            {"name": "Oumé", "region": "Gôh"},
            {"name": "Sinfra", "region": "Marahoué"},
            {"name": "Bouaflé", "region": "Marahoué"},
            {"name": "Zuenoula", "region": "Marahoué"},
            {"name": "Séguéla", "region": "Worodougou"},
            {"name": "Mankono", "region": "Worodougou"},
            {"name": "Kounahiri", "region": "Worodougou"},
            # Villes du nord
            {"name": "Ferkessédougou", "region": "Tchologo"},
            {"name": "Boundiali", "region": "Bagoué"},
            {"name": "Tengréla", "region": "Bagoué"},
            {"name": "Odienné", "region": "Kabadougou"},
            {"name": "Madinani", "region": "Kabadougou"},
            {"name": "Minignan", "region": "Kabadougou"},
            {"name": "Touba", "region": "Bafing"},
            {"name": "Koro", "region": "Bafing"},
            {"name": "Ouaninou", "region": "Bafing"},
            # Villes de l'ouest
            {"name": "Guiglo", "region": "Cavally"},
            {"name": "Toulepleu", "region": "Cavally"},
            {"name": "Bloléquin", "region": "Cavally"},
            {"name": "Duékoué", "region": "Guémon"},
            {"name": "Guiglo", "region": "Guémon"},
            {"name": "Bangolo", "region": "Guémon"},
            {"name": "Danané", "region": "Tonkpi"},
            {"name": "Zouan-Hounien", "region": "Tonkpi"},
            {"name": "Biankouma", "region": "Tonkpi"},
            {"name": "Sipilou", "region": "Tonkpi"},
            {"name": "Kouibly", "region": "Tonkpi"},
            # Villes de l'est
            {"name": "Bondoukou", "region": "Gontougo"},
            {"name": "Tanda", "region": "Gontougo"},
            {"name": "Koun-Fao", "region": "Gontougo"},
            {"name": "Bouna", "region": "Bounkani"},
            {"name": "Nassian", "region": "Bounkani"},
            {"name": "Doropo", "region": "Bounkani"},
            {"name": "Téhini", "region": "Bounkani"},
            {"name": "Bouna", "region": "Bounkani"},
            # Villes du sud-ouest
            {"name": "Soubré", "region": "Nawa"},
            {"name": "Gagnoa", "region": "Nawa"},
            {"name": "Buyo", "region": "Nawa"},
            {"name": "Guéyo", "region": "Nawa"},
            {"name": "Méagui", "region": "Nawa"},
            {"name": "Tabou", "region": "Nawa"},
            {"name": "San-Pédro", "region": "Nawa"},
            {"name": "Sassandra", "region": "Nawa"},
            {"name": "Fresco", "region": "Nawa"},
            # Villes du sud-est
            {"name": "Adzopé", "region": "La Mé"},
            {"name": "Alépé", "region": "La Mé"},
            {"name": "Akoupé", "region": "La Mé"},
            {"name": "Dabou", "region": "Grands-Ponts"},
            {"name": "Grand-Lahou", "region": "Grands-Ponts"},
            {"name": "Jacqueville", "region": "Grands-Ponts"},
            {"name": "Tiassalé", "region": "Grands-Ponts"},
            {"name": "Taabo", "region": "Grands-Ponts"},
            {"name": "N'Douci", "region": "Grands-Ponts"},
            # Villes du centre-ouest
            {"name": "Issia", "region": "Haut-Sassandra"},
            {"name": "Vavoua", "region": "Haut-Sassandra"},
            {"name": "Zoukougbeu", "region": "Haut-Sassandra"},
            {"name": "Séguéla", "region": "Haut-Sassandra"},
            {"name": "Mankono", "region": "Haut-Sassandra"},
            # Villes du centre-nord
            {"name": "Katiola", "region": "Hambol"},
            {"name": "Niakaramandougou", "region": "Hambol"},
            {"name": "Toumodi", "region": "Hambol"},
            {"name": "Béoumi", "region": "Hambol"},
            {"name": "Sakassou", "region": "Hambol"},
            # Villes du centre-est
            {"name": "Dimbokro", "region": "N'Zi"},
            {"name": "Bocanda", "region": "N'Zi"},
            {"name": "Daoukro", "region": "N'Zi"},
            {"name": "M'Bahiakro", "region": "N'Zi"},
            {"name": "Arrah", "region": "N'Zi"},
        ]

        created_count = 0
        updated_count = 0

        for city_data in cities_data:
            city, created = City.objects.get_or_create(
                name=city_data["name"], defaults={"region": city_data["region"]}
            )
            if created:
                created_count += 1
                self.stdout.write(f"✅ Created: {city.name} ({city.region})")
            else:
                updated_count += 1
                self.stdout.write(f"🔄 Updated: {city.name} ({city.region})")

        self.stdout.write(
            self.style.SUCCESS(
                f"\n🎉 Cities import completed!\n"
                f"✅ Created: {created_count} cities\n"
                f"🔄 Updated: {updated_count} cities\n"
                f"📊 Total cities in database: {City.objects.count()}"
            )
        )
