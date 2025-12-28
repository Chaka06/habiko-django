from django import forms
from django.contrib.auth.forms import PasswordChangeForm
from django.core.validators import RegexValidator
from allauth.account.forms import LoginForm, SignupForm
from .models import Profile, RechargePackage, BoostOption, EmailOTP
from ads.models import City


class ProfileEditForm(forms.ModelForm):
    """Formulaire pour modifier le profil"""
    phone_e164 = forms.CharField(
        max_length=20,
        required=False,
        validators=[RegexValidator(r"^\+[1-9]\d{1,14}$", message="Entrez un numéro au format E.164 (+225XXXXXXXXXX)")],
        widget=forms.TextInput(attrs={
            "class": "w-full px-3 py-2 border border-gray-300 rounded-lg",
            "placeholder": "+225XXXXXXXXXX"
        }),
        label="Téléphone",
        help_text="Format: +225XXXXXXXXXX",
    )
    whatsapp_e164 = forms.CharField(
        max_length=20,
        required=False,
        validators=[RegexValidator(r"^\+[1-9]\d{1,14}$", message="Entrez un numéro au format E.164 (+225XXXXXXXXXX)")],
        widget=forms.TextInput(attrs={
            "class": "w-full px-3 py-2 border border-gray-300 rounded-lg",
            "placeholder": "+225XXXXXXXXXX"
        }),
        label="WhatsApp",
        help_text="Format: +225XXXXXXXXXX",
    )
    contact_prefs = forms.MultipleChoiceField(
        choices=[
            ("sms", "SMS"),
            ("whatsapp", "WhatsApp"),
            ("call", "Appel téléphonique"),
        ],
        widget=forms.CheckboxSelectMultiple(attrs={"class": "space-y-2"}),
        required=False,
        label="Méthodes de contact préférées",
    )

    class Meta:
        model = Profile
        fields = ["display_name", "city", "bio_sanitized"]
        widgets = {
            "display_name": forms.TextInput(attrs={
                "class": "w-full px-3 py-2 border border-gray-300 rounded-lg"
            }),
            "city": forms.Select(attrs={
                "class": "w-full px-3 py-2 border border-gray-300 rounded-lg"
            }),
            "bio_sanitized": forms.Textarea(attrs={
                "class": "w-full px-3 py-2 border border-gray-300 rounded-lg",
                "rows": 4
            }),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Pré-remplir whatsapp_e164 depuis le profil
        if self.instance and self.instance.pk:
            self.fields["whatsapp_e164"].initial = self.instance.whatsapp_e164
            if self.instance.contact_prefs:
                self.fields["contact_prefs"].initial = self.instance.contact_prefs


class CustomPasswordChangeForm(PasswordChangeForm):
    """Formulaire personnalisé pour changer le mot de passe"""
    old_password = forms.CharField(
        widget=forms.PasswordInput(attrs={
            "class": "w-full px-3 py-2 border border-gray-300 rounded-lg",
            "autocomplete": "current-password"
        }),
        label="Ancien mot de passe",
    )
    new_password1 = forms.CharField(
        widget=forms.PasswordInput(attrs={
            "class": "w-full px-3 py-2 border border-gray-300 rounded-lg",
            "autocomplete": "new-password"
        }),
        label="Nouveau mot de passe",
    )
    new_password2 = forms.CharField(
        widget=forms.PasswordInput(attrs={
            "class": "w-full px-3 py-2 border border-gray-300 rounded-lg",
            "autocomplete": "new-password"
        }),
        label="Confirmer le nouveau mot de passe",
    )


class PasswordChangeOTPRequestForm(forms.Form):
    """Formulaire pour demander un OTP pour changer le mot de passe"""
    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop("user", None)
        super().__init__(*args, **kwargs)

    def save(self):
        """Crée un OTP pour l'utilisateur"""
        if not self.user:
            raise ValueError("User is required")
        return EmailOTP.create_otp(
            self.user,
            EmailOTP.Purpose.PASSWORD_CHANGE,
            ttl_seconds=600
        )


class RechargeForm(forms.Form):
    """Formulaire pour choisir une formule de recharge"""
    package = forms.ModelChoiceField(
        queryset=RechargePackage.objects.filter(is_active=True),
        widget=forms.RadioSelect(attrs={"class": "space-y-2"}),
        label="Choisissez une formule",
        empty_label=None,
    )


class BoostForm(forms.Form):
    """Formulaire pour booster une annonce"""
    boost_option = forms.ModelChoiceField(
        queryset=BoostOption.objects.filter(is_active=True),
        widget=forms.Select(attrs={"class": "w-full px-3 py-2 border border-gray-300 rounded-lg"}),
        label="Type de boost",
        empty_label="-- Sélectionner --",
    )
    use_free_booster = forms.BooleanField(
        required=False,
        widget=forms.CheckboxInput(attrs={"class": "mr-2"}),
        label="Utiliser un booster gratuit (si disponible)",
        help_text="Vous pouvez utiliser un booster gratuit au lieu de payer",
    )


class CustomLoginForm(LoginForm):
    """
    Formulaire de connexion personnalisé utilisé par allauth.
    Pour l'instant, on garde le comportement par défaut et on se contente
    éventuellement d'ajouter des classes CSS si besoin.
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Ajout de classes Tailwind pour correspondre au design
        self.fields["login"].widget.attrs.update(
            {
                "class": "w-full px-3 py-2 border border-gray-300 rounded-lg",
                "placeholder": "Email",
            }
        )
        self.fields["password"].widget.attrs.update(
            {
                "class": "w-full px-3 py-2 border border-gray-300 rounded-lg",
                "placeholder": "Mot de passe",
            }
        )


class CustomSignupForm(SignupForm):
    """
    Formulaire d'inscription personnalisé utilisé par allauth.
    On garde la logique par défaut, avec seulement un peu de style.
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for name, field in self.fields.items():
            field.widget.attrs.setdefault(
                "class", "w-full px-3 py-2 border border-gray-300 rounded-lg"
            )
