"""
Gestion du consentement aux cookies (RGPD)
"""
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from django.views.decorators.csrf import csrf_exempt
import json


@require_http_methods(["POST"])
@csrf_exempt
def cookie_consent(request):
    """
    Endpoint pour sauvegarder les préférences de cookies
    """
    try:
        data = json.loads(request.body)
        consent = data.get('consent', {})
        
        # Créer une réponse JSON
        response = JsonResponse({'status': 'success'})
        
        # Définir les cookies selon les préférences
        # Cookie essentiel (toujours nécessaire) - httpOnly=False pour que JS puisse le lire
        response.set_cookie(
            'cookie_consent',
            'accepted',
            max_age=365 * 24 * 60 * 60,  # 1 an
            httponly=False,  # Doit être lisible par JavaScript pour vérifier l'affichage
            samesite='Lax',
            secure=not request.META.get('HTTP_X_FORWARDED_PROTO') == 'http'
        )
        
        # Cookies analytiques (Google Analytics)
        if consent.get('analytics', False):
            response.set_cookie(
                'cookie_analytics',
                'accepted',
                max_age=365 * 24 * 60 * 60,
                httponly=False,  # Accessible par JavaScript pour GA
                samesite='Lax',
                secure=not request.META.get('HTTP_X_FORWARDED_PROTO') == 'http'
            )
        else:
            response.set_cookie(
                'cookie_analytics',
                'rejected',
                max_age=365 * 24 * 60 * 60,
                httponly=False,
                samesite='Lax',
                secure=not request.META.get('HTTP_X_FORWARDED_PROTO') == 'http'
            )
        
        # Cookies marketing/publicitaires (si besoin plus tard)
        if consent.get('marketing', False):
            response.set_cookie(
                'cookie_marketing',
                'accepted',
                max_age=365 * 24 * 60 * 60,
                httponly=False,
                samesite='Lax',
                secure=not request.META.get('HTTP_X_FORWARDED_PROTO') == 'http'
            )
        else:
            response.set_cookie(
                'cookie_marketing',
                'rejected',
                max_age=365 * 24 * 60 * 60,
                httponly=False,
                samesite='Lax',
                secure=not request.META.get('HTTP_X_FORWARDED_PROTO') == 'http'
            )
        
        return response
    except Exception as e:
        return JsonResponse({'status': 'error', 'message': str(e)}, status=400)
