"""
IndexNow — Soumet les URLs en temps réel à Bing/Yandex dès publication.
Appelé automatiquement quand une annonce est approuvée.
"""
import logging
import requests

logger = logging.getLogger(__name__)

INDEXNOW_KEY = "6d8dbee3906c43479fba2cabb14b07fe"
SITE_HOST = "ci-kiaba.com"
INDEXNOW_ENDPOINT = "https://api.indexnow.org/indexnow"


def submit_urls(urls: list[str]) -> bool:
    """Soumet une liste d'URLs à IndexNow (Bing, Yandex, etc.)."""
    if not urls:
        return False

    # Filtrer les URLs du bon domaine
    valid = [u for u in urls if SITE_HOST in u]
    if not valid:
        return False

    payload = {
        "host": SITE_HOST,
        "key": INDEXNOW_KEY,
        "keyLocation": f"https://{SITE_HOST}/{INDEXNOW_KEY}.txt",
        "urlList": valid[:10000],  # max 10 000 URLs par appel
    }

    try:
        r = requests.post(
            INDEXNOW_ENDPOINT,
            json=payload,
            timeout=10,
            headers={"Content-Type": "application/json; charset=utf-8"},
        )
        if r.status_code in (200, 202):
            logger.info("IndexNow: %d URL(s) soumises à Bing ✓", len(valid))
            return True
        else:
            logger.warning("IndexNow: réponse inattendue %s — %s", r.status_code, r.text[:200])
            return False
    except Exception as e:
        logger.warning("IndexNow: erreur réseau — %s", e)
        return False


def submit_ad(ad) -> bool:
    """Soumet l'URL d'une annonce à IndexNow."""
    url = f"https://{SITE_HOST}/ads/{ad.slug}/"
    return submit_urls([url])
