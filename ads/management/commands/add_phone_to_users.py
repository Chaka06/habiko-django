"""
Commande pour ajouter des numéros de téléphone aux utilisateurs qui ont des annonces
"""
from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from accounts.models import Profile
import random

User = get_user_model()

# Numéros de téléphone fictifs pour la Côte d'Ivoire
PHONE_NUMBERS = [
    "+2250708091011",
    "+2250708091012",
    "+2250708091013",
    "+2250708091014",
    "+2250708091015",
    "+2250508091011",
    "+2250508091012",
    "+2250508091013",
    "+2250108091011",
    "+2250108091012",
]


class Command(BaseCommand):
    help = "Ajoute des numéros de téléphone aux utilisateurs qui ont des annonces"

    def handle(self, *args, **options):
        # Récupérer tous les utilisateurs qui ont des annonces
        from ads.models import Ad
        user_ids = Ad.objects.values_list('user_id', flat=True).distinct()
        users_with_ads = User.objects.filter(id__in=user_ids)
        
        updated_count = 0
        for user in users_with_ads:
            # Ajouter un numéro de téléphone si manquant
            if not user.phone_e164:
                user.phone_e164 = random.choice(PHONE_NUMBERS)
                user.save()
                self.stdout.write(
                    self.style.SUCCESS(
                        f"✅ Numéro ajouté à {user.username}: {user.phone_e164}"
                    )
                )
                updated_count += 1
            
            # Créer ou mettre à jour le profil
            profile, created = Profile.objects.get_or_create(
                user=user,
                defaults={
                    "display_name": user.username,
                    "whatsapp_e164": user.phone_e164,
                    "contact_prefs": ["sms", "whatsapp", "call"],
                }
            )
            
            if not profile.whatsapp_e164:
                profile.whatsapp_e164 = user.phone_e164
            if not profile.contact_prefs:
                profile.contact_prefs = ["sms", "whatsapp", "call"]
            profile.save()
            
            if created:
                self.stdout.write(
                    self.style.SUCCESS(
                        f"✅ Profil créé pour {user.username}"
                    )
                )
        
        self.stdout.write(
            self.style.SUCCESS(
                f"\n🎉 {updated_count} utilisateur(s) mis à jour avec des numéros de téléphone !"
            )
        )

