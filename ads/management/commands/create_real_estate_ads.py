"""
Commande pour créer des annonces immobilières réalistes avec du vrai contenu
"""
from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from django.utils import timezone
from django.db import transaction
from ads.models import Ad, City, AdMedia
import random
from datetime import timedelta

User = get_user_model()

# Données réalistes pour les annonces immobilières en Côte d'Ivoire
REAL_ESTATE_ADS = [
    {
        "title": "Villa moderne 4 chambres avec piscine à Cocody",
        "category": Ad.Category.VILLAS_RESIDENCES,
        "subcategories": ["Villa avec piscine", "Résidence sécurisée"],
        "description": """Magnifique villa moderne de 250m² située dans le quartier résidentiel de Cocody, à proximité des écoles internationales et du centre commercial.

CARACTÉRISTIQUES :
• 4 chambres avec placards intégrés
• 3 salles de bain modernes
• Salon spacieux avec cheminée
• Cuisine équipée (électroménager inclus)
• Bureau/Home office
• Piscine privée avec terrasse
• Jardin paysager de 500m²
• Garage pour 2 voitures
• Climatisation dans toutes les pièces
• Alarme et système de sécurité
• Quartier sécurisé avec gardiennage

SITUATION :
Quartier calme et résidentiel, à 10 minutes du Plateau, proche des commerces et services. Accès facile aux axes principaux.

Prix : 85 000 000 FCFA
Contactez-nous pour une visite !""",
        "city": "Abidjan",
        "area": "Cocody",
    },
    {
        "title": "Appartement 3 pièces meublé à Marcory",
        "category": Ad.Category.MAISONS_APPARTEMENTS,
        "subcategories": ["Appartement meublé à vendre"],
        "description": """Appartement moderne et lumineux de 90m², entièrement meublé et équipé, situé au 3ème étage d'une résidence sécurisée à Marcory.

COMPOSITION :
• Séjour avec balcon
• 2 chambres avec climatisation
• 1 salle de bain avec douche italienne
• Cuisine équipée (réfrigérateur, four, micro-ondes)
• Meubles de qualité inclus
• Buanderie
• Parking privé

ÉQUIPEMENTS :
• Climatisation réversible
• Eau chaude solaire
• Internet fibre optique
• Ascenseur
• Gardiennage 24/7
• Proximité plage et commerces

Idéal pour investissement locatif ou résidence principale.

Prix : 35 000 000 FCFA""",
        "city": "Abidjan",
        "area": "Marcory",
    },
    {
        "title": "Terrain constructible viabilisé 500m² à Yopougon",
        "category": Ad.Category.TERRAINS,
        "subcategories": ["Terrain constructible", "Terrain viabilisé"],
        "description": """Terrain constructible de 500m², entièrement viabilisé, situé dans un lotissement récent à Yopougon.

CARACTÉRISTIQUES :
• Surface : 500m² (20m x 25m)
• Viabilisé : Électricité, eau, assainissement
• Titre foncier en règle
• Certificat d'urbanisme obtenu
• Quartier en développement
• Accès facile par route bitumée
• Proximité écoles et commerces

IDÉAL POUR :
Construction de villa, maison individuelle ou immeuble locatif.

Prix : 12 000 000 FCFA
Possibilité de financement bancaire.""",
        "city": "Abidjan",
        "area": "Yopougon",
    },
    {
        "title": "Maison à louer 3 chambres à Deux-Plateaux",
        "category": Ad.Category.LOCATIONS,
        "subcategories": ["Maison à louer"],
        "description": """Belle maison de standing à louer dans le quartier résidentiel de Deux-Plateaux.

COMPOSITION :
• 3 chambres avec climatisation
• 2 salles de bain
• Grand salon avec terrasse
• Cuisine équipée
• Jardin arboré
• Garage couvert
• Quartier calme et sécurisé

SERVICES INCLUS :
• Eau et électricité
• Internet disponible
• Gardiennage
• Entretien jardin

Loyer : 450 000 FCFA/mois
Caution : 2 mois
Disponible immédiatement""",
        "city": "Abidjan",
        "area": "Deux-Plateaux",
    },
    {
        "title": "Studio meublé à louer centre-ville Plateau",
        "category": Ad.Category.LOCATIONS,
        "subcategories": ["Studio à louer"],
        "description": """Studio moderne et fonctionnel de 35m², entièrement meublé, situé au cœur du Plateau d'Abidjan.

ÉQUIPEMENTS :
• Lit double avec matelas
• Cuisine équipée (réfrigérateur, plaques)
• Salle de bain avec douche
• Climatisation
• Internet WiFi
• Meubles de rangement
• Proximité bureaux et commerces

IDÉAL POUR :
Étudiant, jeune professionnel ou personne seule.

Loyer : 180 000 FCFA/mois
Charges comprises
Disponible dès maintenant""",
        "city": "Abidjan",
        "area": "Plateau",
    },
    {
        "title": "Villa de luxe 5 chambres avec jardin à Riviera",
        "category": Ad.Category.VILLAS_RESIDENCES,
        "subcategories": ["Villa de luxe", "Villa avec piscine", "Résidence sécurisée"],
        "description": """Prestigieuse villa de standing de 350m² sur terrain de 800m², dans le quartier huppé de Riviera.

PRESTATIONS :
• 5 chambres avec dressing
• 4 salles de bain de luxe
• Grand salon avec cheminée
• Salle à manger
• Cuisine professionnelle équipée
• Bureau privé
• Piscine avec pool house
• Jardin paysager avec éclairage
• Garage 3 voitures
• Domotique complète
• Système de sécurité avancé
• Quartier VIP avec gardiennage

EXCLUSIVITÉ :
Villa de très haut standing, idéale pour famille nombreuse ou réceptions.

Prix : 150 000 000 FCFA
Visite sur rendez-vous uniquement.""",
        "city": "Abidjan",
        "area": "Riviera",
    },
    {
        "title": "Appartement 2 pièces à vendre à Abobo",
        "category": Ad.Category.MAISONS_APPARTEMENTS,
        "subcategories": ["Appartement à vendre"],
        "description": """Appartement de 65m² au 2ème étage, dans une résidence récente à Abobo.

COMPOSITION :
• Séjour avec cuisine ouverte
• 2 chambres
• 1 salle de bain
• Balcon avec vue
• Parking
• Résidence sécurisée

AVANTAGES :
• Prix accessible
• Proximité transports
• Quartier animé
• Commerces à proximité

Prix : 18 000 000 FCFA
Facilités de paiement possibles.""",
        "city": "Abidjan",
        "area": "Abobo",
    },
    {
        "title": "Terrain commercial 300m² à Koumassi",
        "category": Ad.Category.TERRAINS,
        "subcategories": ["Terrain commercial"],
        "description": """Terrain commercial de 300m², idéalement situé sur axe principal à Koumassi, zone à fort trafic.

CARACTÉRISTIQUES :
• Surface : 300m² (15m x 20m)
• Face route bitumée
• Titre foncier
• Zone commerciale autorisée
• Forte visibilité
• Passage important

IDÉAL POUR :
Station-service, supermarché, restaurant, commerce de détail.

Prix : 25 000 000 FCFA
Investissement rentable.""",
        "city": "Abidjan",
        "area": "Koumassi",
    },
    {
        "title": "Résidence meublée à louer à Cocody Angré",
        "category": Ad.Category.LOCATIONS,
        "subcategories": ["Résidence meublée à louer"],
        "description": """Résidence moderne entièrement meublée de 120m², dans résidence sécurisée à Cocody Angré.

COMPOSITION :
• 3 chambres climatisées
• 2 salles de bain
• Salon spacieux
• Cuisine équipée complète
• Terrasse privée
• Jardin commun
• Parking privé

ÉQUIPEMENTS INCLUS :
• Meubles de qualité
• Électroménager complet
• Linge de maison
• Internet fibre
• Climatisation
• Eau chaude

Loyer : 550 000 FCFA/mois
Charges : 50 000 FCFA/mois
Disponible immédiatement""",
        "city": "Abidjan",
        "area": "Cocody",
    },
    {
        "title": "Maison 4 chambres avec cour à Bouaké",
        "category": Ad.Category.MAISONS_APPARTEMENTS,
        "subcategories": ["Maison à vendre"],
        "description": """Belle maison familiale de 180m² sur terrain de 400m², dans quartier calme de Bouaké.

COMPOSITION :
• 4 chambres
• 2 salles de bain
• Grand salon
• Cuisine séparée
• Grande cour arrière
• Garage
• Jardin avant

SITUATION :
Quartier résidentiel calme, proche centre-ville, écoles et hôpital.

Prix : 28 000 000 FCFA
Visite possible tous les jours.""",
        "city": "Bouaké",
        "area": "Centre-ville",
    },
    {
        "title": "Duplex moderne à vendre à Daloa",
        "category": Ad.Category.MAISONS_APPARTEMENTS,
        "subcategories": ["Duplex à vendre"],
        "description": """Duplex moderne de 150m² sur 2 niveaux, dans résidence récente à Daloa.

RÉPARTITION :
Rez-de-chaussée :
• Salon, cuisine, salle à manger
• 1 chambre, 1 salle de bain

Étage :
• 2 chambres avec balcon
• 1 salle de bain
• Bureau

ÉQUIPEMENTS :
• Climatisation
• Eau chaude
• Parking
• Résidence sécurisée

Prix : 32 000 000 FCFA
Facilités de paiement.""",
        "city": "Daloa",
        "area": "Zone résidentielle",
    },
    {
        "title": "Terrain agricole 2 hectares à Yamoussoukro",
        "category": Ad.Category.TERRAINS,
        "subcategories": ["Terrain agricole"],
        "description": """Grand terrain agricole de 2 hectares (20 000m²), idéal pour agriculture ou élevage, à Yamoussoukro.

CARACTÉRISTIQUES :
• Surface : 2 hectares
• Sol fertile
• Accès route
• Point d'eau disponible
• Clôture partielle
• Titre foncier

IDÉAL POUR :
Culture maraîchère, élevage, projet agricole.

Prix : 8 000 000 FCFA
Prix négociable pour achat comptant.""",
        "city": "Yamoussoukro",
        "area": "Périphérie",
    },
]


class Command(BaseCommand):
    help = "Crée des annonces immobilières réalistes avec du vrai contenu"

    def add_arguments(self, parser):
        parser.add_argument(
            "--count",
            type=int,
            default=12,
            help="Nombre d'annonces à créer (défaut: 12)",
        )

    def handle(self, *args, **options):
        count = options["count"]
        
        # Récupérer ou créer les villes
        cities = {}
        for ad_data in REAL_ESTATE_ADS:
            city_name = ad_data["city"]
            if city_name not in cities:
                city, _ = City.objects.get_or_create(
                    name=city_name,
                    defaults={"region": "Côte d'Ivoire"}
                )
                cities[city_name] = city
        
        # Créer un utilisateur de test si nécessaire
        user, _ = User.objects.get_or_create(
            username="habiko_immobilier",
            defaults={
                "email": "contact@habiko-ci.com",
                "is_active": True,
                "phone_e164": "+2250708091011",  # Numéro de téléphone pour afficher les contacts
            }
        )
        
        # S'assurer que l'utilisateur a un numéro de téléphone
        if not user.phone_e164:
            user.phone_e164 = "+2250708091011"
            user.save()
        
        # Créer ou mettre à jour le profil avec les préférences de contact
        from accounts.models import Profile
        profile, _ = Profile.objects.get_or_create(
            user=user,
            defaults={
                "display_name": "HABIKO Immobilier",
                "whatsapp_e164": "+2250708091011",
                "contact_prefs": ["sms", "whatsapp", "call"],
            }
        )
        if not profile.whatsapp_e164:
            profile.whatsapp_e164 = "+2250708091011"
        if not profile.contact_prefs:
            profile.contact_prefs = ["sms", "whatsapp", "call"]
        profile.save()
        
        created = 0
        with transaction.atomic():
            # Prendre les annonces demandées (ou toutes si count > nombre d'annonces)
            ads_to_create = REAL_ESTATE_ADS[:count] if count <= len(REAL_ESTATE_ADS) else REAL_ESTATE_ADS
            
            for ad_data in ads_to_create:
                city = cities[ad_data["city"]]
                
                # Vérifier si l'annonce existe déjà
                existing = Ad.objects.filter(
                    title=ad_data["title"],
                    city=city
                ).first()
                
                if existing:
                    self.stdout.write(
                        self.style.WARNING(f"Annonce existante: {ad_data['title']}")
                    )
                    continue
                
                # Créer l'annonce
                ad = Ad.objects.create(
                    user=user,
                    title=ad_data["title"],
                    description_sanitized=ad_data["description"],
                    category=ad_data["category"],
                    subcategories=ad_data["subcategories"],
                    city=city,
                    area=ad_data.get("area", ""),
                    status=Ad.Status.APPROVED,
                    is_verified=random.choice([True, False]),
                    expires_at=timezone.now() + timedelta(days=random.randint(30, 90)),
                    created_at=timezone.now() - timedelta(days=random.randint(1, 30)),
                )
                
                created += 1
                self.stdout.write(
                    self.style.SUCCESS(f"✅ Annonce créée: {ad.title} ({city.name})")
                )
        
        self.stdout.write(
            self.style.SUCCESS(
                f"\n🎉 {created} annonce(s) immobilière(s) créée(s) avec succès !"
            )
        )
        self.stdout.write(
            self.style.SUCCESS(
                "💡 Pour ajouter des images, utilisez l'interface d'administration ou téléchargez des images dans le dossier media/ads/"
            )
        )

