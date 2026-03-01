"""
Service PawaPay — intégration REST v2 pour les dépôts mobile money (Côte d'Ivoire).

Correspondants CI supportés :
  MTN_MOMO_CIV   — MTN Mobile Money Côte d'Ivoire
  ORANGE_CIV     — Orange Money Côte d'Ivoire
  WAVE_CIV       — Wave Côte d'Ivoire
  MOOV_MONEY_CIV — Moov Money Côte d'Ivoire

Sandbox : https://api.sandbox.pawapay.io
Production : https://api.pawapay.io
"""
import logging
import requests
from django.conf import settings

logger = logging.getLogger(__name__)

_SANDBOX_URL = "https://api.sandbox.pawapay.io"
_PROD_URL = "https://api.pawapay.io"

# Correspondants CIV disponibles (clé = provider PawaPay, valeur = libellé affiché)
CORRESPONDENTS = {
    "MTN_MOMO_CIV": "MTN Mobile Money",
    "ORANGE_CIV": "Orange Money",
    "WAVE_CIV": "Wave",
    "MOOV_MONEY_CIV": "Moov Money",
}


def _base_url() -> str:
    if getattr(settings, "PAWAPAY_SANDBOX", True):
        return _SANDBOX_URL
    return _PROD_URL


def _headers() -> dict:
    token = getattr(settings, "PAWAPAY_API_TOKEN", "") or ""
    return {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
    }


def initiate_deposit(deposit_id: str, amount: int, phone: str, correspondent: str, description: str) -> dict:
    """
    Lance un dépôt PawaPay v2 (le client reçoit une notification push sur son téléphone).

    :param deposit_id: UUID v4 généré par nous (clé d'idempotence)
    :param amount: montant en FCFA (entier)
    :param phone: numéro MSISDN sans le « + » (ex: 2250700000000)
    :param correspondent: MTN_MOMO_CIV | ORANGE_CIV | WAVE_CIV | MOOV_MONEY_CIV
    :param description: texte sur le relevé (max 22 caractères, alphanumérique + espaces)
    :returns: dict réponse PawaPay
    :raises: requests.HTTPError si le statut HTTP est >= 400
    """
    # customerMessage : max 22 chars, alphanumérique + espaces uniquement
    import re
    safe_desc = re.sub(r"[^a-zA-Z0-9 ]", "", description or "KIABA")[:22]

    payload = {
        "depositId": str(deposit_id),
        "amount": str(amount),
        "currency": "XOF",
        "payer": {
            "type": "MMO",
            "accountDetails": {
                "provider": correspondent,
                "phoneNumber": phone,
            },
        },
        "customerMessage": safe_desc,
    }

    logger.info("PawaPay initiate_deposit %s — %s FCFA via %s", deposit_id, amount, correspondent)

    resp = requests.post(
        f"{_base_url()}/v2/deposits",
        json=payload,
        headers=_headers(),
        timeout=15,
    )
    resp.raise_for_status()
    data = resp.json()
    logger.info("PawaPay response for %s: status=%s", deposit_id, data.get("status"))
    return data


def check_deposit(deposit_id: str) -> dict:
    """
    Vérifie le statut d'un dépôt PawaPay v2.

    :returns: dict avec au minimum la clé « status » (ACCEPTED|SUBMITTED|COMPLETED|FAILED)
    """
    resp = requests.get(
        f"{_base_url()}/v2/deposits/{deposit_id}",
        headers=_headers(),
        timeout=10,
    )
    resp.raise_for_status()
    return resp.json()
