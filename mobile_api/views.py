"""
API REST pour l'application mobile KIABA Rencontres.
Authentification par Token (rest_framework.authtoken).
"""
import json
import logging
from functools import wraps

from django.contrib.auth import authenticate, get_user_model
from django.core.paginator import Paginator
from django.db.models import Case, When, Value, IntegerField, Q
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from django.utils import timezone
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError

from rest_framework.authtoken.models import Token

from ads.models import Ad, City, Favorite
from payments.models import Payment

User = get_user_model()
logger = logging.getLogger(__name__)


# ── Helpers ────────────────────────────────────────────────────────────────────

def json_body(request):
    try:
        return json.loads(request.body)
    except (json.JSONDecodeError, ValueError):
        return {}


def get_token_user(request):
    """Retourne l'utilisateur authentifié via Token, ou None."""
    auth = request.headers.get("Authorization", "")
    if not auth.startswith("Token "):
        return None
    key = auth.split(" ", 1)[1].strip()
    try:
        token = Token.objects.select_related("user").get(key=key)
        return token.user
    except Token.DoesNotExist:
        return None


def require_auth(f):
    """Décorateur — retourne 401 si pas authentifié."""
    @wraps(f)
    def wrapper(request, *args, **kwargs):
        user = get_token_user(request)
        if user is None:
            return JsonResponse({"detail": "Authentification requise."}, status=401)
        request.api_user = user
        return f(request, *args, **kwargs)
    return wrapper


def serialize_user(user):
    profile = getattr(user, "userprofile", None)
    return {
        "id": user.id,
        "username": user.username,
        "email": user.email,
        "phone_e164": getattr(user, "phone_e164", None),
        "is_verified": getattr(user, "is_verified", False),
        "role": getattr(user, "role", "provider"),
        "profile": {
            "display_name": profile.display_name if profile else user.username,
            "avatar": profile.avatar.url if profile and profile.avatar else None,
        } if profile else None,
    }


def serialize_ad(ad, request=None):
    medias = []
    for m in ad.media.all():
        img_url = None
        thumb_url = None
        if m.image:
            img_url = request.build_absolute_uri(m.image.url) if request else m.image.url
        if m.thumbnail:
            thumb_url = request.build_absolute_uri(m.thumbnail.url) if request else m.thumbnail.url
        medias.append({
            "id": m.id,
            "image": img_url,
            "thumbnail": thumb_url,
            "is_primary": m.is_primary,
        })

    user_data = None
    if hasattr(ad, "user") and ad.user:
        user_data = {
            "id": ad.user.id,
            "username": ad.user.username,
            "is_verified": getattr(ad.user, "is_verified", False),
        }

    phone = None
    if hasattr(ad, "additional_data") and ad.additional_data:
        phone = ad.additional_data.get("phone") or ad.additional_data.get("whatsapp")

    # Chercher le téléphone dans le profil utilisateur
    if not phone:
        profile = getattr(ad.user, "userprofile", None)
        if profile:
            phone = getattr(profile, "whatsapp_e164", None) or getattr(profile, "phone2_e164", None)

    return {
        "id": ad.id,
        "title": ad.title,
        "description_sanitized": ad.description_sanitized,
        "category": ad.category,
        "category_display": ad.get_category_display(),
        "slug": ad.slug,
        "city": {"id": ad.city.id, "name": ad.city.name, "slug": ad.city.slug},
        "status": ad.status,
        "is_premium": ad.is_premium,
        "is_urgent": ad.is_urgent,
        "is_boosted": ad.is_boosted,
        "is_verified": ad.is_verified,
        "boost_interval_hours": ad.boost_interval_hours,
        "subcategories": ad.subcategories or [],
        "media": medias,
        "created_at": ad.created_at.isoformat(),
        "expires_at": ad.expires_at.isoformat() if ad.expires_at else None,
        "views_count": ad.views_count,
        "phone": phone,
        "price": ad.additional_data.get("price") if ad.additional_data else None,
        "user": user_data,
    }


# ── Auth ───────────────────────────────────────────────────────────────────────

@csrf_exempt
@require_http_methods(["POST"])
def api_login(request):
    data = json_body(request)
    email = data.get("email", "").strip()
    password = data.get("password", "")
    if not email or not password:
        return JsonResponse({"detail": "Email et mot de passe requis."}, status=400)
    user = authenticate(request, username=email, password=password)
    if user is None:
        # allauth stocke l'email comme username parfois — essayer avec username
        try:
            u = User.objects.get(email=email)
            user = authenticate(request, username=u.username, password=password)
        except User.DoesNotExist:
            pass
    if user is None:
        return JsonResponse({"detail": "Email ou mot de passe incorrect."}, status=401)
    if not user.is_active:
        return JsonResponse({"detail": "Compte désactivé."}, status=403)
    token, _ = Token.objects.get_or_create(user=user)
    return JsonResponse({"token": token.key, "user": serialize_user(user)})


@csrf_exempt
@require_http_methods(["POST"])
def api_register(request):
    data = json_body(request)
    username = data.get("username", "").strip()
    email = data.get("email", "").strip()
    password = data.get("password1") or data.get("password", "")
    phone = data.get("phone_e164", "").strip()

    if not username or not email or not password:
        return JsonResponse({"detail": "Pseudo, email et mot de passe requis."}, status=400)

    if User.objects.filter(email=email).exists():
        return JsonResponse({"detail": "Un compte existe déjà avec cet email."}, status=400)
    if User.objects.filter(username=username).exists():
        return JsonResponse({"detail": "Ce pseudo est déjà utilisé."}, status=400)

    try:
        validate_password(password)
    except ValidationError as e:
        return JsonResponse({"detail": " ".join(e.messages)}, status=400)

    user = User.objects.create_user(username=username, email=email, password=password)
    if phone:
        try:
            user.phone_e164 = phone
            user.save(update_fields=["phone_e164"])
        except Exception:
            pass

    token, _ = Token.objects.get_or_create(user=user)
    return JsonResponse({"token": token.key, "user": serialize_user(user)}, status=201)


@csrf_exempt
@require_http_methods(["POST"])
@require_auth
def api_logout(request):
    try:
        request.api_user.auth_token.delete()
    except Exception:
        pass
    return JsonResponse({"detail": "Déconnecté."})


@csrf_exempt
@require_http_methods(["GET"])
@require_auth
def api_me(request):
    return JsonResponse(serialize_user(request.api_user))


@csrf_exempt
@require_http_methods(["POST"])
@require_auth
def api_change_password(request):
    data = json_body(request)
    old = data.get("old_password", "")
    new = data.get("new_password1") or data.get("new_password", "")
    user = request.api_user
    if not user.check_password(old):
        return JsonResponse({"detail": "Ancien mot de passe incorrect."}, status=400)
    try:
        validate_password(new, user=user)
    except ValidationError as e:
        return JsonResponse({"detail": " ".join(e.messages)}, status=400)
    user.set_password(new)
    user.save()
    # Renouveler le token
    Token.objects.filter(user=user).delete()
    token = Token.objects.create(user=user)
    return JsonResponse({"detail": "Mot de passe modifié.", "token": token.key})


# ── Annonces ───────────────────────────────────────────────────────────────────

@csrf_exempt
@require_http_methods(["GET"])
def api_ads_list(request):
    qs = Ad.objects.select_related("city", "user").prefetch_related("media").filter(
        status__in=[Ad.Status.APPROVED, Ad.Status.EXPIRED],
        image_processing_done=True,
    )

    # Filtres
    city_slug = request.GET.get("city", "").strip()
    category = request.GET.get("category", "").strip()
    q = request.GET.get("q", "").strip()

    if city_slug:
        qs = qs.filter(city__slug=city_slug)
    if category:
        qs = qs.filter(category=category)
    if q:
        qs = qs.filter(Q(title__icontains=q) | Q(description_sanitized__icontains=q))

    # Tri : approuvées d'abord, puis expirées
    qs = qs.annotate(
        expired_order=Case(
            When(status=Ad.Status.EXPIRED, then=Value(1)),
            default=Value(0),
            output_field=IntegerField(),
        )
    ).order_by("expired_order", "-is_premium", "-is_boosted", "-is_urgent", "-created_at")

    # Pagination
    page_num = int(request.GET.get("page", 1))
    paginator = Paginator(qs, 20)
    page = paginator.get_page(page_num)

    results = [serialize_ad(ad, request) for ad in page.object_list]
    return JsonResponse({
        "count": paginator.count,
        "next": page.next_page_number() if page.has_next() else None,
        "previous": page.previous_page_number() if page.has_previous() else None,
        "results": results,
    })


@csrf_exempt
@require_http_methods(["GET"])
def api_ad_detail(request, pk):
    try:
        ad = Ad.objects.select_related("city", "user").prefetch_related("media").get(pk=pk)
    except Ad.DoesNotExist:
        return JsonResponse({"detail": "Annonce introuvable."}, status=404)
    return JsonResponse(serialize_ad(ad, request))


@csrf_exempt
@require_http_methods(["GET"])
@require_auth
def api_my_ads(request):
    qs = Ad.objects.select_related("city").prefetch_related("media").filter(
        user=request.api_user
    ).order_by("-created_at")
    return JsonResponse({"results": [serialize_ad(ad, request) for ad in qs]})


@csrf_exempt
@require_http_methods(["DELETE", "POST"])
@require_auth
def api_delete_ad(request, pk):
    try:
        ad = Ad.objects.get(pk=pk, user=request.api_user)
    except Ad.DoesNotExist:
        return JsonResponse({"detail": "Annonce introuvable."}, status=404)
    ad.delete()
    return JsonResponse({"detail": "Annonce supprimée."})


@csrf_exempt
@require_http_methods(["GET"])
def api_cities(request):
    cities = City.objects.all().order_by("name")
    return JsonResponse({
        "results": [{"id": c.id, "name": c.name, "slug": c.slug} for c in cities]
    })


# ── Favoris ────────────────────────────────────────────────────────────────────

@csrf_exempt
@require_http_methods(["GET"])
@require_auth
def api_favorites(request):
    favs = Favorite.objects.filter(user=request.api_user).select_related(
        "ad__city", "ad__user"
    ).prefetch_related("ad__media").order_by("-created_at")
    return JsonResponse({
        "results": [serialize_ad(f.ad, request) for f in favs if f.ad]
    })


@csrf_exempt
@require_http_methods(["POST"])
@require_auth
def api_toggle_favorite(request, pk):
    try:
        ad = Ad.objects.get(pk=pk)
    except Ad.DoesNotExist:
        return JsonResponse({"detail": "Annonce introuvable."}, status=404)
    fav, created = Favorite.objects.get_or_create(user=request.api_user, ad=ad)
    if not created:
        fav.delete()
        return JsonResponse({"favorited": False})
    return JsonResponse({"favorited": True})


@csrf_exempt
@require_http_methods(["GET"])
@require_auth
def api_check_favorite(request, pk):
    exists = Favorite.objects.filter(user=request.api_user, ad_id=pk).exists()
    return JsonResponse({"favorited": exists})


# ── Paiements ──────────────────────────────────────────────────────────────────

@csrf_exempt
@require_http_methods(["GET"])
@require_auth
def api_payment_history(request):
    payments = Payment.objects.filter(user=request.api_user).select_related("ad").order_by("-created_at")
    results = []
    for p in payments:
        results.append({
            "deposit_id": str(p.deposit_id),
            "type": p.type,
            "type_display": p.get_type_display(),
            "forfait": p.get_type_display(),
            "amount": p.amount,
            "status": p.status,
            "status_display": p.get_status_display(),
            "ad_id": p.ad_id,
            "ad_title": p.ad.title if p.ad else None,
            "ad_slug": p.ad.slug if p.ad else None,
            "operator": getattr(p, "operator", None),
            "created_at": p.created_at.isoformat(),
            "completed_at": p.completed_at.isoformat() if getattr(p, "completed_at", None) else None,
        })
    return JsonResponse({"results": results})


@csrf_exempt
@require_http_methods(["POST"])
def api_check_promo(request):
    from payments.models import PromoCode
    data = json_body(request)
    code = data.get("code", "").strip().upper()
    if not code:
        return JsonResponse({"detail": "Code requis."}, status=400)
    try:
        promo = PromoCode.objects.get(code=code, active=True)
        if not promo.is_valid():
            return JsonResponse({"detail": "Code expiré ou épuisé."}, status=400)
        return JsonResponse({"discount_percent": promo.discount_percent, "code": promo.code})
    except PromoCode.DoesNotExist:
        return JsonResponse({"detail": "Code invalide."}, status=404)
