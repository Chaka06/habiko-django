"""
Commande pour créer les options de boost
"""
from django.core.management.base import BaseCommand
from accounts.models import BoostOption


class Command(BaseCommand):
    help = "Crée les options de boost"

    def handle(self, *args, **options):
        # Options Premium
        premium_options = [
            {"duration_days": 3, "price": 1000},
            {"duration_days": 7, "price": 2900},
            {"duration_days": 15, "price": 5800},
            {"duration_days": 30, "price": 8100},
            {"duration_days": 45, "price": 15700},
            {"duration_days": 60, "price": 20300},
            {"duration_days": 90, "price": 30800},
        ]

        # Options Prolongation
        prolongation_options = [
            {"duration_days": 45, "price": 1600},
            {"duration_days": 90, "price": 2900},
            {"duration_days": 180, "price": 5500},
            {"duration_days": 365, "price": 30100},
        ]

        # Options Urgent
        urgent_options = [
            {"duration_days": 7, "price": 2600},
            {"duration_days": 15, "price": 4200},
            {"duration_days": 30, "price": 7200},
        ]

        created = 0
        updated = 0

        # Créer les options Premium
        for opt in premium_options:
            boost, created_flag = BoostOption.objects.get_or_create(
                boost_type=BoostOption.BoostType.PREMIUM,
                duration_days=opt["duration_days"],
                defaults={
                    "name": f"Premium {opt['duration_days']} jours",
                    "price": opt["price"],
                }
            )
            if created_flag:
                created += 1
                self.stdout.write(
                    self.style.SUCCESS(f"✓ Créé: {boost.name}")
                )
            else:
                boost.price = opt["price"]
                boost.save()
                updated += 1
                self.stdout.write(
                    self.style.WARNING(f"→ Mis à jour: {boost.name}")
                )

        # Créer les options Prolongation
        for opt in prolongation_options:
            boost, created_flag = BoostOption.objects.get_or_create(
                boost_type=BoostOption.BoostType.PROLONGATION,
                duration_days=opt["duration_days"],
                defaults={
                    "name": f"Prolongation +{opt['duration_days']} jours",
                    "price": opt["price"],
                }
            )
            if created_flag:
                created += 1
                self.stdout.write(
                    self.style.SUCCESS(f"✓ Créé: {boost.name}")
                )
            else:
                boost.price = opt["price"]
                boost.save()
                updated += 1
                self.stdout.write(
                    self.style.WARNING(f"→ Mis à jour: {boost.name}")
                )

        # Créer les options Urgent
        for opt in urgent_options:
            boost, created_flag = BoostOption.objects.get_or_create(
                boost_type=BoostOption.BoostType.URGENT,
                duration_days=opt["duration_days"],
                defaults={
                    "name": f"Urgent {opt['duration_days']} jours",
                    "price": opt["price"],
                }
            )
            if created_flag:
                created += 1
                self.stdout.write(
                    self.style.SUCCESS(f"✓ Créé: {boost.name}")
                )
            else:
                boost.price = opt["price"]
                boost.save()
                updated += 1
                self.stdout.write(
                    self.style.WARNING(f"→ Mis à jour: {boost.name}")
                )

        self.stdout.write(
            self.style.SUCCESS(
                f"\n{created} options créées, {updated} options mises à jour"
            )
        )


