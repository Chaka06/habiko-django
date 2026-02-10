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
        
        # Sous-catégories : mêmes choix pour toutes les catégories (escorte_girl, escorte_boy, transgenre)
        self.fields["subcategories"].choices = self.get_subcategory_choices(category or "escorte_girl")
        if category:
            self.add_category_fields(category)
    
    def add_category_fields(self, category):
        """Ajoute des champs dynamiques selon la catégorie"""
        base_attrs = {
            "class": "w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-orange-500 focus:border-orange-500"
        }
        
        # Pour KIABA (annonces adultes), on ne gère plus les champs
        # immobiliers spécifiques (surface, chambres, etc.) ici.
        # On garde uniquement les champs génériques du formulaire.
        return

    def get_subcategory_choices(self, category):
        """Retourne les sous-catégories (toujours les mêmes pour escorte_girl/boy/transgenre)."""
        # Une seule source de vérité : le modèle Ad
        choices = getattr(Ad, "SUBCATEGORY_CHOICES", None) or [
            "Sex vaginal",
            "Sex anal (sodomie)",
            "Massage sexuel",
            "Massage du corps",
        ]
        return [(c, c) for c in choices]

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
