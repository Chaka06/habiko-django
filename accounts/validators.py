"""
Validateurs réutilisables partagés entre les models et les formulaires.
Centralise la logique de validation pour éviter la duplication de code.
"""
from django.core.validators import RegexValidator
from django.utils.translation import gettext_lazy as _

# Validateur E.164 : format international de numéro de téléphone (+225XXXXXXXXXX)
# Utilisé sur CustomUser.phone_e164, Profile.whatsapp_e164, Profile.phone2_e164, AdForm.phone1/phone2
E164_VALIDATOR = RegexValidator(
    r"^\+[1-9]\d{1,14}$",
    message=_("Entrez un numéro au format E.164 (ex: +225XXXXXXXXXX)"),
)
