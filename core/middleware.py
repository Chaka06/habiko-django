import ipaddress
import re

from django.http import HttpRequest, HttpResponsePermanentRedirect, HttpResponse
from django.shortcuts import redirect
from django.conf import settings
from django.middleware.csrf import get_token
import gzip
from io import BytesIO

# Plages IP officielles Cloudflare (source : https://www.cloudflare.com/ips/)
# Mises à jour : octobre 2024
_CLOUDFLARE_IP_RANGES = [
    # IPv4
    "103.21.244.0/22",
    "103.22.200.0/22",
    "103.31.4.0/22",
    "104.16.0.0/13",
    "104.24.0.0/14",
    "108.162.192.0/18",
    "131.0.72.0/22",
    "141.101.64.0/18",
    "162.158.0.0/15",
    "172.64.0.0/13",
    "173.245.48.0/20",
    "188.114.96.0/20",
    "190.93.240.0/20",
    "197.234.240.0/22",
    "198.41.128.0/17",
    # IPv6
    "2400:cb00::/32",
    "2606:4700::/32",
    "2803:f800::/32",
    "2405:b500::/32",
    "2405:8100::/32",
    "2a06:98c0::/29",
    "2c0f:f248::/32",
]

# Réseau compilés une seule fois au démarrage (évite le parsing répété)
_CF_NETWORKS: list | None = None


def _get_cf_networks():
    global _CF_NETWORKS
    if _CF_NETWORKS is None:
        _CF_NETWORKS = [ipaddress.ip_network(r) for r in _CLOUDFLARE_IP_RANGES]
    return _CF_NETWORKS


def _is_cloudflare_ip(ip_str: str) -> bool:
    """Retourne True si l'IP appartient aux plages officielles Cloudflare."""
    try:
        ip = ipaddress.ip_address(ip_str)
        return any(ip in net for net in _get_cf_networks())
    except ValueError:
        return False

# Chemins allauth : exemption CSRF pour tous les formulaires d’auth
AUTH_CSRF_EXEMPT_PATHS = ("/auth/login/", "/auth/signup/", "/auth/password/reset/")
AUTH_CSRF_EXEMPT_RESET_KEY = re.compile(r"^/auth/password/reset/key/[0-9A-Za-z]+-.+")


def _is_auth_form_post(request: HttpRequest) -> bool:
    """POST vers login, signup ou réinitialisation mot de passe."""
    if request.method != "POST":
        return False
    path = (request.path or "").rstrip("/")
    if path in (p.rstrip("/") for p in AUTH_CSRF_EXEMPT_PATHS):
        return True
    return bool(AUTH_CSRF_EXEMPT_RESET_KEY.match(request.path))


class RedirectMiddleware:
    """
    Middleware pour gérer les redirections :
    - HTTP vers HTTPS
    - www vers non-www (ou vice versa)
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request: HttpRequest):
        # En développement (DEBUG=True), désactiver toutes les redirections
        if settings.DEBUG:
            return self.get_response(request)

        # Vérifier HTTPS en tenant compte des proxies (Render, etc.)
        # Vérifier d'abord le header X-Forwarded-Proto (pour les proxies)
        forwarded_proto = request.META.get("HTTP_X_FORWARDED_PROTO", "")
        is_https = request.is_secure() or forwarded_proto == "https"

        # Redirection HTTP vers HTTPS (uniquement en production)
        if not is_https:
            # Construire l'URL HTTPS avec tous les paramètres
            url = request.build_absolute_uri().replace("http://", "https://", 1)
            response = HttpResponsePermanentRedirect(url)
            # Ajouter des headers pour aider Google à comprendre la redirection
            response["Cache-Control"] = "public, max-age=3600"
            return response

        # Redirection www vers non-www DÉSACTIVÉE : sur Vercel, seul www.ci-kiaba.com peut être
        # configuré (ci-kiaba.com non-www absent). La redirection provoquait 404 ou "CSRF cookie not set"
        # car le cookie n'était jamais posé sur www (301 sans Set-Cookie). Garder www actif.
        # host = request.get_host()
        # if host.startswith("www."):
        #     url = request.build_absolute_uri().replace("www.", "", 1)
        #     ...

        # Si on arrive ici, la requête est valide (HTTPS ou DEBUG)
        # On laisse passer normalement
        return self.get_response(request)


class CloudflareMiddleware:
    """
    Middleware pour récupérer l'IP réelle du client depuis Cloudflare
    Cloudflare envoie l'IP réelle dans le header CF-Connecting-IP
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # Cloudflare envoie l'IP réelle dans ce header.
        # On ne fait confiance à ce header QUE si la requête vient d'une IP Cloudflare connue
        # pour éviter l'usurpation d'IP par un attaquant passant directement au serveur.
        cf_connecting_ip = request.META.get("HTTP_CF_CONNECTING_IP")
        remote_addr = request.META.get("REMOTE_ADDR", "")

        if cf_connecting_ip and _is_cloudflare_ip(remote_addr):
            request.META["REMOTE_ADDR"] = cf_connecting_ip.strip()
            request.META["HTTP_X_FORWARDED_FOR_ORIGINAL"] = request.META.get(
                "HTTP_X_FORWARDED_FOR", ""
            )

        response = self.get_response(request)
        return response


class CsrfExemptPasswordResetFromKeyMiddleware:
    """
    Exempte du CSRF tous les formulaires d’auth (connexion, inscription, réinitialisation mot de passe).
    """
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request: HttpRequest):
        if _is_auth_form_post(request):
            # Django n'utilise pas request.csrf_exempt mais getattr(callback, 'csrf_exempt').
            # _dont_enforce_csrf_checks est reconnu par CsrfViewMiddleware (tests + notre cas).
            request._dont_enforce_csrf_checks = True
        return self.get_response(request)


class EnsureCsrfCookieForAuthMiddleware:
    """
    Force le dépôt du cookie CSRF lors d'un GET sur les pages d'auth (connexion,
    inscription, réinitialisation mot de passe). Évite l'erreur « CSRF cookie not set »
    quand l'utilisateur arrive depuis un lien (ex. email) ou un nouvel onglet.
    """
    AUTH_PREFIX = "/auth/"

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request: HttpRequest):
        if request.method == "GET" and request.path.startswith(self.AUTH_PREFIX):
            get_token(request)
        return self.get_response(request)


# Clé session utilisée par django.contrib.messages (SessionStorage)
MESSAGES_SESSION_KEY = "_messages"


class ConsumeMessagesAfterResponseMiddleware:
    """
    Après chaque réponse 200, vide la liste des messages en session pour qu'ils
    ne réapparaissent jamais sur les pages suivantes. On ne touche pas en cas de
    redirection (302) pour que « Connexion réussie » s'affiche une fois sur la page d'arrivée.
    """
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request: HttpRequest):
        response = self.get_response(request)
        if response.status_code == 200 and hasattr(request, "session"):
            if MESSAGES_SESSION_KEY in request.session:
                del request.session[MESSAGES_SESSION_KEY]
                request.session.modified = True
        return response


class AgeGateMiddleware:
    """
    Middleware pour l'age-gate (réglable via ENABLE_AGE_GATE dans settings).
    Peut être activé pour KIABA Rencontres (site 18+) si besoin.
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request: HttpRequest):
        # Age-gate désactivé par défaut. Pour activer (site 18+), mettre ENABLE_AGE_GATE = True dans settings.
        from django.conf import settings

        enable_age_gate = getattr(settings, "ENABLE_AGE_GATE", False)

        if not enable_age_gate:
            return self.get_response(request)

        # Utilisateurs connectés : pas d'age gate (modale ni redirect)
        if getattr(request, "user", None) and request.user.is_authenticated:
            return self.get_response(request)

        # Sinon la page se charge normalement ; la modale 18+ est gérée en JS (sessionStorage)
        # dans base.html : réapparaît à chaque nouvelle session (après fermeture du navigateur).
        return self.get_response(request)


class GZipCompressionMiddleware:
    """
    Middleware pour compresser les réponses avec gzip
    Améliore les performances en réduisant la taille des réponses HTTP
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request: HttpRequest):
        response = self.get_response(request)

        # Ne compresser que les réponses HTML, CSS, JS, JSON, XML
        content_type = response.get("Content-Type", "")
        compressible_types = [
            "text/html",
            "text/css",
            "text/javascript",
            "application/javascript",
            "application/json",
            "application/xml",
            "text/xml",
        ]

        # Vérifier si le type de contenu est compressible
        should_compress = any(ct in content_type for ct in compressible_types)

        # Vérifier si le client accepte gzip
        accept_encoding = request.META.get("HTTP_ACCEPT_ENCODING", "")
        accepts_gzip = "gzip" in accept_encoding

        # Ne pas compresser si déjà compressé ou si trop petit (< 200 bytes)
        if (
            should_compress
            and accepts_gzip
            and "Content-Encoding" not in response
            and len(response.content) > 200
        ):

            # Compresser le contenu
            compressed_content = BytesIO()
            with gzip.GzipFile(fileobj=compressed_content, mode="wb") as gz_file:
                gz_file.write(response.content)
            compressed_content.seek(0)

            # Créer une nouvelle réponse avec le contenu compressé
            compressed_response = HttpResponse(
                compressed_content.read(),
                content_type=response.get("Content-Type"),
                status=response.status_code,
            )

            # Copier les headers de la réponse originale
            for header, value in response.items():
                if header.lower() != "content-length":
                    compressed_response[header] = value

            # Copier les cookies (Set-Cookie) — response.items() ne les inclut pas
            for cookie_name, cookie_morsel in response.cookies.items():
                compressed_response.cookies[cookie_name] = cookie_morsel

            # Ajouter le header Content-Encoding
            compressed_response["Content-Encoding"] = "gzip"
            compressed_response["Content-Length"] = str(len(compressed_response.content))
            compressed_response["Vary"] = "Accept-Encoding"

            return compressed_response

        return response


class StaticMediaCacheMiddleware:
    """
    Ajoute des headers de cache agressifs pour les fichiers statiques et les images d'annonces.
    - /static/ : géré en grande partie par WhiteNoise, mais on renforce si besoin
    - /media/ads/ : images d'annonces, rarement modifiées -> cache long (1 an)
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request: HttpRequest):
        response = self.get_response(request)

        path = request.path or ""
        # Ne traiter que les réponses 200 pour GET/HEAD
        if request.method in ("GET", "HEAD") and response.status_code == 200:
            # Images d'annonces
            if path.startswith("/media/ads/"):
                response["Cache-Control"] = "public, max-age=31536000, immutable"
            # Ressources statiques (en complément de WhiteNoise)
            elif path.startswith("/static/"):
                # Ne pas raccourcir un cache déjà plus agressif
                existing = response.get("Cache-Control", "")
                if not existing:
                    response["Cache-Control"] = "public, max-age=31536000, immutable"

        return response
