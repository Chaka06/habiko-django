"""
Décorateurs de contrôle d'accès basés sur les rôles (RBAC).
Utiliser ces décorateurs sur les vues sensibles pour appliquer le modèle de rôles.
"""
from functools import wraps

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect


def role_required(*roles):
    """
    Décorateur générique : autorise uniquement les utilisateurs ayant l'un des rôles spécifiés.
    Redirige vers /dashboard/ avec un message d'erreur si le rôle est insuffisant.

    Usage:
        @role_required("moderator", "admin")
        def ma_vue(request): ...
    """
    def decorator(view_func):
        @wraps(view_func)
        @login_required
        def _wrapped_view(request, *args, **kwargs):
            if not hasattr(request.user, "role") or request.user.role not in roles:
                messages.error(
                    request,
                    "Accès refusé. Vous n'avez pas les droits nécessaires pour accéder à cette page.",
                )
                return redirect("/dashboard/")
            return view_func(request, *args, **kwargs)
        return _wrapped_view
    return decorator


def moderator_required(view_func):
    """
    Décorateur : autorise uniquement les modérateurs et administrateurs.

    Usage:
        @moderator_required
        def approuver_annonce(request, ad_id): ...
    """
    return role_required("moderator", "admin")(view_func)


def admin_required(view_func):
    """
    Décorateur : autorise uniquement les administrateurs.

    Usage:
        @admin_required
        def vue_admin(request): ...
    """
    return role_required("admin")(view_func)
