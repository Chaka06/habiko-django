from django.http import HttpRequest, HttpResponsePermanentRedirect
from django.shortcuts import redirect
from django.conf import settings


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
        forwarded_proto = request.META.get('HTTP_X_FORWARDED_PROTO', '')
        is_https = request.is_secure() or forwarded_proto == 'https'
        
        # Redirection HTTP vers HTTPS (uniquement en production)
        if not is_https:
            # Construire l'URL HTTPS avec tous les paramètres
            url = request.build_absolute_uri().replace('http://', 'https://', 1)
            response = HttpResponsePermanentRedirect(url)
            # Ajouter des headers pour aider Google à comprendre la redirection
            response['Cache-Control'] = 'public, max-age=3600'
            return response
        
        # Redirection www vers non-www (ou l'inverse selon votre préférence)
        host = request.get_host()
        if host.startswith('www.'):
            # Rediriger www.ci-habiko.com vers ci-habiko.com
            url = request.build_absolute_uri().replace('www.', '', 1)
            response = HttpResponsePermanentRedirect(url)
            # Ajouter des headers pour aider Google à comprendre la redirection
            response['Cache-Control'] = 'public, max-age=3600'
            return response
        
        # Si on arrive ici, la requête est valide (HTTPS ou DEBUG)
        # On laisse passer normalement
        return self.get_response(request)


class AgeGateMiddleware:
    """
    Middleware pour l'age-gate (désactivé pour HABIKO - site immobilier)
    Peut être réactivé si nécessaire en changeant ENABLE_AGE_GATE dans settings
    """
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request: HttpRequest):
        # Désactiver l'age-gate pour HABIKO (site immobilier, pas de restriction d'âge)
        # Pour réactiver, ajouter ENABLE_AGE_GATE = True dans settings
        from django.conf import settings
        enable_age_gate = getattr(settings, 'ENABLE_AGE_GATE', False)
        
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
        
        client_ip = request.META.get('REMOTE_ADDR', '')
        if client_ip.startswith('66.249.') or client_ip.startswith('64.233.') or client_ip.startswith('72.14.'):
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
