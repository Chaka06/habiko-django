import re

from django.http import HttpRequest, HttpResponsePermanentRedirect, HttpResponse
from django.shortcuts import redirect
from django.conf import settings
from django.middleware.csrf import get_token
import gzip
from io import BytesIO

# Chemins allauth réinitialisation mot de passe (exemption CSRF si session/cookie absents)
PASSWORD_RESET_REQUEST_PATH = "/auth/password/reset/"
PASSWORD_RESET_FROM_KEY_PATH = re.compile(r"^/auth/password/reset/key/[0-9A-Za-z]+-.+")


def _is_password_reset_post(request: HttpRequest) -> bool:
    """POST vers « mot de passe oublié » (saisie email) ou « définir nouveau mot de passe » (lien email)."""
    if request.method != "POST":
        return False
    if request.path.rstrip("/") == PASSWORD_RESET_REQUEST_PATH.rstrip("/"):
        return True
    return bool(PASSWORD_RESET_FROM_KEY_PATH.match(request.path))


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
        # Cloudflare envoie l'IP réelle dans ce header
        cf_connecting_ip = request.META.get("HTTP_CF_CONNECTING_IP")
        if cf_connecting_ip:
            # Remplacer REMOTE_ADDR par l'IP réelle du client
            request.META["REMOTE_ADDR"] = cf_connecting_ip
            # Garder aussi l'IP originale dans un header personnalisé
            request.META["HTTP_X_FORWARDED_FOR_ORIGINAL"] = request.META.get(
                "HTTP_X_FORWARDED_FOR", ""
            )

        response = self.get_response(request)
        return response


class CsrfExemptPasswordResetFromKeyMiddleware:
    """
    Exempte du CSRF les formulaires réinitialisation mot de passe (saisie email + lien email).
    Évite « Vérification de sécurité » quand session/cookie ne sont pas envoyés. Abus limité par rate-limit allauth.
    """
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request: HttpRequest):
        if _is_password_reset_post(request):
            request.csrf_exempt = True
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


class ConsumeMessagesAfterResponseMiddleware:
    """
    Après chaque réponse HTML (200), consomme les messages pour qu'ils ne
    réapparaissent pas sur les pages suivantes. On ne touche pas aux messages
    en cas de redirection (302) pour que « Connexion réussie » etc. s'affichent
    une fois sur la page d'arrivée.
    """
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request: HttpRequest):
        response = self.get_response(request)
        if response.status_code == 200:
            try:
                from django.contrib import messages
                list(messages.get_messages(request))
            except Exception:
                pass
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
            # Age-gate désactivé, laisser passer toutes les requêtes
            return self.get_response(request)

        # Code original de l'age-gate (conservé au cas où)
        path = request.path
        user_agent = request.META.get("HTTP_USER_AGENT", "").lower()

        # Detect search engine crawlers and allow them to bypass age gate
        is_search_engine = any(
            bot in user_agent
            for bot in [
                "googlebot",
                "google-inspectiontool",
                "bingbot",
                "slurp",
                "duckduckbot",
                "baiduspider",
                "yandexbot",
                "sogou",
                "exabot",
                "facebot",
                "ia_archiver",
                "ahrefsbot",
                "semrushbot",
                "mj12bot",
            ]
        )

        client_ip = request.META.get("REMOTE_ADDR", "")
        if (
            client_ip.startswith("66.249.")
            or client_ip.startswith("64.233.")
            or client_ip.startswith("72.14.")
        ):
            is_search_engine = True

        if not request.COOKIES.get("age_gate_accepted") and not is_search_engine:
            allowed = (
                path.startswith("/age-gate/")
                or path.startswith("/admin/")
                or path.startswith("/auth/")
                or path.startswith("/static/")
                or path.startswith("/media/")
                or path == "/robots.txt"
                or path == "/sitemap.xml"
                or path.startswith("/google")
            )
            if not allowed:
                return redirect("/age-gate/")
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
