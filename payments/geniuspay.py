"""
Service GeniusPay — API v1 pour les paiements mobile money et carte (Côte d'Ivoire).

Base URL : https://pay.genius.ci/api/v1/merchant
Auth     : X-API-Key + X-API-Secret (headers)
Checkout : redirection vers la page GeniusPay (choix de l'opérateur côté client)

Webhook  : POST JSON signé HMAC-SHA256
  signature = HMAC-SHA256(timestamp + "." + json_payload, webhook_secret)
  Headers  : X-Webhook-Signature, X-Webhook-Timestamp, X-Webhook-Event
"""
import hashlib
import hmac
import logging
import time

import requests
from django.conf import settings

logger = logging.getLogger(__name__)

_BASE_URL = "https://pay.genius.ci/api/v1/merchant"


def _headers() -> dict:
    return {
        "X-API-Key": getattr(settings, "GENIUSPAY_API_KEY", ""),
        "X-API-Secret": getattr(settings, "GENIUSPAY_API_SECRET", ""),
        "Content-Type": "application/json",
    }


def create_payment(
    amount: int,
    description: str,
    success_url: str,
    error_url: str,
    metadata: dict = None,
    payment_method: str = None,
    mmo_provider: str = None,
    customer_phone: str = None,
) -> dict:
    """
    Crée un paiement GeniusPay en mode checkout.
    Le client choisit son moyen de paiement (Wave, Orange, MTN, Moov, Carte)
    sur la page GeniusPay hébergée.

    :param amount: Montant en XOF (min 200)
    :param description: Description du paiement (max 500 caractères)
    :param success_url: URL de retour après succès
    :param error_url: URL de retour après échec
    :param metadata: Données personnalisées (ex: {'deposit_id': '...'})
    :param customer_name: Nom du client (optionnel)
    :param customer_email: Email du client (optionnel)
    :returns: dict avec 'checkout_url', 'reference', 'id', 'status', etc.
    :raises requests.HTTPError: si le statut HTTP >= 400
    """
    payload: dict = {
        "amount": amount,
        "currency": "XOF",
        "description": description[:500],
        "success_url": success_url,
        "error_url": error_url,
    }

    if payment_method:
        payload["payment_method"] = payment_method
    if mmo_provider:
        payload["mmo_provider"] = mmo_provider
    if customer_phone:
        payload["customer"] = {"phone": customer_phone}
    if metadata:
        payload["metadata"] = metadata

    logger.info("GeniusPay create_payment payload: %s", payload)

    resp = requests.post(
        f"{_BASE_URL}/payments",
        json=payload,
        headers=_headers(),
        timeout=8,
    )
    resp.raise_for_status()
    body = resp.json()
    data = body.get("data", body)
    logger.info(
        "GeniusPay response FULL: reference=%s payment_url=%s checkout_url=%s keys=%s",
        data.get("reference"),
        data.get("payment_url"),
        data.get("checkout_url"),
        list(data.keys()),
    )
    return data


def get_payment(reference: str) -> dict:
    """
    Récupère les détails d'un paiement par sa référence GeniusPay.

    :returns: dict avec au minimum 'status' (pending|processing|completed|failed|cancelled|refunded)
    """
    resp = requests.get(
        f"{_BASE_URL}/payments/{reference}",
        headers=_headers(),
        timeout=10,
    )
    resp.raise_for_status()
    body = resp.json()
    return body.get("data", body)


def verify_webhook_signature(timestamp: str, payload_bytes: bytes, signature: str) -> bool:
    """
    Vérifie la signature HMAC-SHA256 d'un webhook GeniusPay.

    Format : HMAC-SHA256(timestamp + "." + json_payload_bytes, webhook_secret)
    Protection replay : timestamp doit être dans les 5 dernières minutes.

    :param timestamp: Header X-Webhook-Timestamp (Unix timestamp en string)
    :param payload_bytes: Corps brut de la requête (bytes)
    :param signature: Header X-Webhook-Signature
    :returns: True si la signature est valide
    """
    secret = getattr(settings, "GENIUSPAY_WEBHOOK_SECRET", "")
    if not secret:
        if settings.DEBUG:
            logger.warning("GENIUSPAY_WEBHOOK_SECRET non configuré — signature non vérifiée (DEBUG)")
            return True
        # En production, refuser tout webhook sans secret configuré
        logger.error("GENIUSPAY_WEBHOOK_SECRET non configuré en production — webhook rejeté")
        return False

    try:
        # Anti-replay : timestamp max 5 minutes
        ts = int(timestamp)
        if abs(int(time.time()) - ts) > 300:
            logger.warning("GeniusPay webhook: timestamp trop ancien (%s)", timestamp)
            return False

        data_to_sign = timestamp.encode() + b"." + payload_bytes
        expected = hmac.new(
            secret.encode("utf-8"),
            data_to_sign,
            hashlib.sha256,
        ).hexdigest()
        return hmac.compare_digest(expected, signature)

    except Exception as exc:
        logger.warning("GeniusPay webhook signature check exception: %s", exc)
        return False
