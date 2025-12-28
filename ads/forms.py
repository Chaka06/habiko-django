from django import forms
from django.core.exceptions import ValidationError
import bleach
from .models import Ad, City


class AdForm(forms.Form):
    """Formulaire unique pour créer une annonce"""

    title = forms.CharField(
        max_length=140,
        widget=forms.TextInput(
            attrs={
                "class": "w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-orange-500 focus:border-orange-500",
                "placeholder": "Titre de votre annonce",
            }
        ),
        label="Titre de l'annonce",
    )

    category = forms.ChoiceField(
        choices=Ad.Category.choices,
        widget=forms.Select(
            attrs={
                "class": "w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
            }
        ),
        label="Catégorie",
    )

    subcategories = forms.MultipleChoiceField(
        choices=[],
        widget=forms.CheckboxSelectMultiple(attrs={"class": "space-y-2"}),
        required=False,
        label="Sous-catégories",
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # Déterminer la catégorie sélectionnée
        category = None
        # Si le formulaire est lié (bound), récupérer depuis les données POST
        if args and len(args) > 0:
            # args[0] peut être un QueryDict (request.POST) ou un dict
            data = args[0]
            if hasattr(data, 'get'):
                category = data.get("category")
        # Sinon, vérifier dans kwargs
        if not category:
            if "data" in kwargs:
                category = kwargs["data"].get("category")
            elif "initial" in kwargs and "category" in kwargs["initial"]:
                category = kwargs["initial"].get("category")
        
        # Mettre à jour les sous-catégories selon la catégorie sélectionnée
        if category:
            self.fields["subcategories"].choices = self.get_subcategory_choices(category)
            # Ajouter les champs dynamiques selon la catégorie
            self.add_category_fields(category)
        else:
            # Toujours initialiser avec toutes les sous-catégories possibles pour éviter les erreurs de validation
            if not self.fields["subcategories"].choices:
                all_subcategories = []
                for category_choices in (
                    self.get_subcategory_choices("maisons_appartements")
                    + self.get_subcategory_choices("villas_residences")
                    + self.get_subcategory_choices("terrains")
                    + self.get_subcategory_choices("locations")
                ):
                    all_subcategories.append(category_choices)
                self.fields["subcategories"].choices = all_subcategories
    
    def add_category_fields(self, category):
        """Ajoute des champs dynamiques selon la catégorie"""
        base_attrs = {
            "class": "w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-orange-500 focus:border-orange-500"
        }
        
        if category == "villas_residences":
            # Pour les résidences meublées : prix jours ouvrables et non ouvrables
            self.fields["prix_jours_ouvrables"] = forms.DecimalField(
                required=False,
                max_digits=10,
                decimal_places=0,
                widget=forms.NumberInput(attrs={**base_attrs, "placeholder": "Prix en FCFA"}),
                label="Prix jours ouvrables (FCFA/jour)",
                help_text="Prix pour les jours ouvrables (lundi-vendredi)"
            )
            self.fields["prix_jours_non_ouvrables"] = forms.DecimalField(
                required=False,
                max_digits=10,
                decimal_places=0,
                widget=forms.NumberInput(attrs={**base_attrs, "placeholder": "Prix en FCFA"}),
                label="Prix jours non ouvrables (FCFA/jour)",
                help_text="Prix pour les weekends et jours fériés"
            )
            self.fields["surface"] = forms.IntegerField(
                required=False,
                widget=forms.NumberInput(attrs={**base_attrs, "placeholder": "Surface en m²"}),
                label="Surface (m²)",
            )
            self.fields["nombre_chambres"] = forms.IntegerField(
                required=False,
                widget=forms.NumberInput(attrs={**base_attrs, "placeholder": "Nombre de chambres"}),
                label="Nombre de chambres",
            )
        
        elif category == "maisons_appartements":
            # Pour les maisons/appartements à vendre : prix, surface, chambres, salles de bain
            self.fields["prix_vente"] = forms.DecimalField(
                required=False,
                max_digits=12,
                decimal_places=0,
                widget=forms.NumberInput(attrs={**base_attrs, "placeholder": "Prix en FCFA"}),
                label="Prix de vente (FCFA)",
            )
            self.fields["surface"] = forms.IntegerField(
                required=False,
                widget=forms.NumberInput(attrs={**base_attrs, "placeholder": "Surface en m²"}),
                label="Surface (m²)",
            )
            self.fields["nombre_chambres"] = forms.IntegerField(
                required=False,
                widget=forms.NumberInput(attrs={**base_attrs, "placeholder": "Nombre de chambres"}),
                label="Nombre de chambres",
            )
            self.fields["nombre_salles_bain"] = forms.IntegerField(
                required=False,
                widget=forms.NumberInput(attrs={**base_attrs, "placeholder": "Nombre de salles de bain"}),
                label="Nombre de salles de bain",
            )
        
        elif category == "terrains":
            # Pour les terrains : prix, surface
            self.fields["prix"] = forms.DecimalField(
                required=False,
                max_digits=12,
                decimal_places=0,
                widget=forms.NumberInput(attrs={**base_attrs, "placeholder": "Prix en FCFA"}),
                label="Prix (FCFA)",
            )
            self.fields["surface"] = forms.IntegerField(
                required=False,
                widget=forms.NumberInput(attrs={**base_attrs, "placeholder": "Surface en m²"}),
                label="Surface (m²)",
            )
        
        elif category == "locations":
            # Pour les locations : loyer, charges, caution
            self.fields["loyer_mensuel"] = forms.DecimalField(
                required=False,
                max_digits=10,
                decimal_places=0,
                widget=forms.NumberInput(attrs={**base_attrs, "placeholder": "Loyer en FCFA"}),
                label="Loyer mensuel (FCFA)",
            )
            self.fields["charges"] = forms.DecimalField(
                required=False,
                max_digits=10,
                decimal_places=0,
                widget=forms.NumberInput(attrs={**base_attrs, "placeholder": "Charges en FCFA"}),
                label="Charges (FCFA/mois)",
                help_text="Charges mensuelles (eau, électricité, etc.)"
            )
            self.fields["caution"] = forms.DecimalField(
                required=False,
                max_digits=10,
                decimal_places=0,
                widget=forms.NumberInput(attrs={**base_attrs, "placeholder": "Caution en FCFA"}),
                label="Caution (FCFA)",
                help_text="Dépôt de garantie"
            )
            self.fields["surface"] = forms.IntegerField(
                required=False,
                widget=forms.NumberInput(attrs={**base_attrs, "placeholder": "Surface en m²"}),
                label="Surface (m²)",
            )
            self.fields["nombre_chambres"] = forms.IntegerField(
                required=False,
                widget=forms.NumberInput(attrs={**base_attrs, "placeholder": "Nombre de chambres"}),
                label="Nombre de chambres",
            )

    def get_subcategory_choices(self, category):
        """Retourne les sous-catégories selon la catégorie"""
        subcategory_mapping = {
            "maisons_appartements": [
                "Maison à vendre",
                "Appartement à vendre",
                "Studio à vendre",
                "Duplex à vendre",
                "Villa à vendre",
                "Maison meublée à vendre",
                "Appartement meublé à vendre",
            ],
            "villas_residences": [
                "Villa de luxe",
                "Résidence meublée",
                "Résidence de standing",
                "Villa avec piscine",
                "Résidence sécurisée",
            ],
            "terrains": [
                "Terrain à vendre",
                "Terrain constructible",
                "Terrain viabilisé",
                "Parcelle à vendre",
                "Terrain commercial",
            ],
            "locations": [
                "Maison à louer",
                "Appartement à louer",
                "Studio à louer",
                "Villa à louer",
                "Résidence meublée à louer",
            ],
        }
        subcategories = subcategory_mapping.get(category, [])
        return [(choice, choice) for choice in subcategories]

    def clean_subcategories(self):
        # Convertir la liste en JSON pour le stockage
        subcategories = self.cleaned_data.get("subcategories", [])
        return subcategories

    description = forms.CharField(
        widget=forms.Textarea(
            attrs={
                "class": "w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-orange-500 focus:border-orange-500",
                "rows": 5,
                "placeholder": "Description détaillée de votre annonce...",
            }
        ),
        label="Description",
    )

    city = forms.ModelChoiceField(
        queryset=City.objects.all(),
        widget=forms.Select(
            attrs={
                "class": "w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
            }
        ),
        label="Ville",
    )

    phone1 = forms.CharField(
        max_length=20,
        widget=forms.TextInput(
            attrs={
                "class": "w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-orange-500 focus:border-orange-500",
                "placeholder": "+225XXXXXXXXX",
            }
        ),
        label="Numéro de téléphone 1",
        help_text="Numéro principal pour les appels et SMS",
    )

    phone2 = forms.CharField(
        max_length=20,
        required=False,
        widget=forms.TextInput(
            attrs={
                "class": "w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-orange-500 focus:border-orange-500",
                "placeholder": "+225XXXXXXXXX (optionnel)",
            }
        ),
        label="Numéro de téléphone 2 (optionnel)",
    )

    contact_methods = forms.MultipleChoiceField(
        choices=[
            ("sms", "SMS"),
            ("whatsapp", "WhatsApp"),
            ("call", "Appel téléphonique"),
        ],
        widget=forms.CheckboxSelectMultiple(attrs={"class": "space-y-2"}),
        required=True,
        label="Méthodes de contact",
        help_text="Sélectionnez les moyens par lesquels les clients peuvent vous contacter",
    )

    image1 = forms.ImageField(
        required=False,
        widget=forms.ClearableFileInput(
            attrs={
                "class": "w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-orange-500 focus:border-orange-500",
                "accept": "image/*",
            }
        ),
        label="Photo 1",
    )

    image2 = forms.ImageField(
        required=False,
        widget=forms.ClearableFileInput(
            attrs={
                "class": "w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-orange-500 focus:border-orange-500",
                "accept": "image/*",
            }
        ),
        label="Photo 2",
    )

    image3 = forms.ImageField(
        required=False,
        widget=forms.ClearableFileInput(
            attrs={
                "class": "w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-orange-500 focus:border-orange-500",
                "accept": "image/*",
            }
        ),
        label="Photo 3",
    )

    image4 = forms.ImageField(
        required=False,
        widget=forms.ClearableFileInput(
            attrs={
                "class": "w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-orange-500 focus:border-orange-500",
                "accept": "image/*",
            }
        ),
        label="Photo 4",
    )

    image5 = forms.ImageField(
        required=False,
        widget=forms.ClearableFileInput(
            attrs={
                "class": "w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-orange-500 focus:border-orange-500",
                "accept": "image/*",
            }
        ),
        label="Photo 5",
    )

    def clean_description(self):
        description = self.cleaned_data["description"]
        # Sanitize HTML avec bleach
        sanitized = bleach.clean(description, tags=[], attributes={}, strip=True)
        return sanitized

    def clean(self):
        cleaned_data = super().clean()
        phone1 = cleaned_data.get("phone1")
        phone2 = cleaned_data.get("phone2")
        contact_methods = cleaned_data.get("contact_methods")

        if not phone1 and not phone2:
            raise ValidationError("Au moins un numéro de téléphone est requis.")

        if contact_methods and not (phone1 or phone2):
            self.add_error(
                "contact_methods",
                "Vous devez fournir un numéro de téléphone pour les méthodes de contact sélectionnées.",
            )

        return cleaned_data
