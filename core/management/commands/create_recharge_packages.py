"""
Commande pour créer les formules de recharge
"""
from django.core.management.base import BaseCommand
from accounts.models import RechargePackage


class Command(BaseCommand):
    help = "Crée les formules de recharge"

    def handle(self, *args, **options):
        packages = [
            {
                "name": "Pack 4000 FCFA",
                "amount": 4000,
                "ads_included": 3,
                "credit_amount": 4000,
                "free_boosters": 0,
                "is_premium": False,
            },
            {
                "name": "Pack 6000 FCFA",
                "amount": 6000,
                "ads_included": 5,
                "credit_amount": 6000,
                "free_boosters": 0,
                "is_premium": False,
            },
            {
                "name": "Pack 10000 FCFA",
                "amount": 10000,
                "ads_included": 8,
                "credit_amount": 10000,
                "free_boosters": 0,
                "is_premium": False,
            },
            {
                "name": "Pack 15000 FCFA",
                "amount": 15000,
                "ads_included": 10,
                "credit_amount": 15000,
                "free_boosters": 2,
                "is_premium": False,
            },
            {
                "name": "Pack Premium 20000 FCFA",
                "amount": 20000,
                "ads_included": 15,
                "credit_amount": 0,
                "free_boosters": 0,
                "is_premium": True,
            },
        ]

        created = 0
        for pkg_data in packages:
            pkg, created_flag = RechargePackage.objects.get_or_create(
                amount=pkg_data["amount"],
                defaults=pkg_data
            )
            if created_flag:
                created += 1
                self.stdout.write(
                    self.style.SUCCESS(f"✓ Créé: {pkg.name}")
                )
            else:
                # Mettre à jour si existe déjà
                for key, value in pkg_data.items():
                    setattr(pkg, key, value)
                pkg.save()
                self.stdout.write(
                    self.style.WARNING(f"→ Mis à jour: {pkg.name}")
                )

        self.stdout.write(
            self.style.SUCCESS(f"\n{created} formules créées/mises à jour")
        )


