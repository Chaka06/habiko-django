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

    # Téléphone : d'abord phone_e164 de l'utilisateur (champ principal du site web)
    phone = None
    if ad.user:
        phone = getattr(ad.user, "phone_e164", None) or None
        if not phone:
            profile = getattr(ad.user, "userprofile", None)
            if profile:
                phone = (getattr(profile, "whatsapp_e164", None) or
                         getattr(profile, "phone2_e164", None) or None)
    # Fallback : additional_data
    if not phone and ad.additional_data:
        phone = ad.additional_data.get("phone") or ad.additional_data.get("whatsapp") or None

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
@require_http_methods(["POST"])
@require_auth
def api_create_ad(request):
    """Créer une annonce via multipart/form-data (identique au formulaire web)."""
    from django.utils.text import slugify
    import uuid

    user = request.api_user

    title = request.POST.get("title", "").strip()
    description = request.POST.get("description", "").strip()
    category = request.POST.get("category", "").strip()
    city_id = request.POST.get("city", "").strip()
    phone1 = request.POST.get("phone1", "").strip()
    phone2 = request.POST.get("phone2", "").strip()
    contact_methods = request.POST.getlist("contact_methods")
    subcategories = request.POST.getlist("subcategories")

    if not title:
        return JsonResponse({"detail": "Titre requis."}, status=400)
    if not description or len(description) < 20:
        return JsonResponse({"detail": "Description trop courte (min 20 caractères)."}, status=400)
    if category not in [c[0] for c in Ad.Category.choices]:
        return JsonResponse({"detail": "Catégorie invalide."}, status=400)
    if not city_id:
        return JsonResponse({"detail": "Ville requise."}, status=400)

    try:
        city = City.objects.get(pk=int(city_id))
    except (City.DoesNotExist, ValueError):
        return JsonResponse({"detail": "Ville introuvable."}, status=400)

    # Sauvegarder les téléphones sur le profil utilisateur (même logique que le site web)
    if phone1:
        user.phone_e164 = phone1
        user.save(update_fields=["phone_e164"])
    if phone1 or phone2:
        try:
            profile = user.userprofile
            if phone2:
                profile.whatsapp_e164 = phone2
                profile.phone2_e164 = phone2
            elif phone1:
                profile.whatsapp_e164 = phone1
            if contact_methods:
                profile.contact_prefs = contact_methods
            profile.save()
        except Exception:
            pass

    # Générer un slug unique
    base_slug = slugify(title) or "annonce"
    slug = base_slug
    counter = 1
    while Ad.objects.filter(slug=slug).exists():
        slug = f"{base_slug}-{counter}"
        counter += 1

    ad = Ad.objects.create(
        user=user,
        title=title,
        description_sanitized=description,
        category=category,
        subcategories=subcategories,
        city=city,
        status=Ad.Status.PENDING,
        slug=slug,
    )

    # Traiter les images
    images = request.FILES.getlist("images")
    if images:
        from ads.models import AdMedia
        for i, image in enumerate(images[:5]):
            AdMedia.objects.create(ad=ad, image=image, is_primary=(i == 0))
        ad.image_processing_done = False
        ad.save(update_fields=["image_processing_done"])

    return JsonResponse(serialize_ad(ad, request), status=201)


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
@require_auth
def api_mobile_initiate_payment(request):
    """
    Initie un paiement GeniusPay pour une annonce DRAFT.
    Body JSON: { "ad_id": 42, "forfait": "standard"|"bundle"|"fortnight"|"monthly", "promo_code": "" }
    Retourne: { "checkout_url": "...", "deposit_id": "...", "amount": 1000, "original_amount": 1000 }
    """
    from payments.models import Payment, PromoCodeUsage
    from payments import geniuspay as gp_svc
    from payments.views import PRICE_STANDARD, PRICE_BUNDLE, PRICE_FORTNIGHT, PRICE_MONTHLY

    data = json_body(request)
    ad_id = data.get("ad_id")
    forfait = data.get("forfait", "")
    promo_code = (data.get("promo_code") or "").strip().upper()

    try:
        ad = Ad.objects.get(pk=int(ad_id), user=request.api_user, status=Ad.Status.DRAFT)
    except (Ad.DoesNotExist, TypeError, ValueError):
        return JsonResponse({"detail": "Annonce introuvable ou déjà payée."}, status=404)

    FORFAIT_MAP = {
        "standard":  (Payment.Type.STANDARD,  PRICE_STANDARD,  "KIABA Annonce 5j"),
        "bundle":    (Payment.Type.BUNDLE,     PRICE_BUNDLE,    "KIABA Annonce 5j + Boost"),
        "fortnight": (Payment.Type.FORTNIGHT,  PRICE_FORTNIGHT, "KIABA Pack 15j + Boost"),
        "monthly":   (Payment.Type.MONTHLY,    PRICE_MONTHLY,   "KIABA Pack mensuel + Boost"),
    }
    if forfait not in FORFAIT_MAP:
        return JsonResponse({"detail": "Forfait invalide."}, status=400)

    pay_type, amount, desc = FORFAIT_MAP[forfait]
    original_amount = amount
    discount_fcfa = 0

    # Code promo
    if promo_code:
        from payments.models import PromoCode
        try:
            promo = PromoCode.objects.get(code=promo_code)
            if not promo.is_valid():
                return JsonResponse({"detail": "Code promo expiré ou épuisé."}, status=400)
            if PromoCodeUsage.objects.filter(code=promo_code, user=request.api_user).exists():
                return JsonResponse({"detail": "Code promo déjà utilisé sur votre compte."}, status=400)
            discount_fcfa = int(amount * promo.discount_percent / 100)
            amount = max(amount - discount_fcfa, 1)
        except PromoCode.DoesNotExist:
            return JsonResponse({"detail": "Code promo invalide."}, status=400)

    # URL de retour (page web GeniusPay → site KIABA)
    success_url = f"https://ci-kiaba.com/pay/return/{{deposit_id}}/"
    error_url = f"https://ci-kiaba.com/pay/return/{{deposit_id}}/?failed=1"

    payment = Payment.objects.create(
        user=request.api_user,
        ad=ad,
        type=pay_type,
        amount=amount,
    )

    # Remplir les URLs avec le deposit_id réel
    success_url = f"https://ci-kiaba.com/pay/return/{payment.deposit_id}/"
    error_url = f"https://ci-kiaba.com/pay/return/{payment.deposit_id}/?failed=1"

    try:
        gp_data = gp_svc.create_payment(
            amount=payment.amount,
            description=desc,
            success_url=success_url,
            error_url=error_url,
            metadata={
                "deposit_id": str(payment.deposit_id),
                "type": payment.type,
                "ad_id": ad.id,
                "source": "mobile",
            },
        )
        payment.geniuspay_reference = gp_data.get("reference", "")
        payment.gateway_response = gp_data
        payment.save(update_fields=["geniuspay_reference", "gateway_response"])

        checkout_url = gp_data.get("checkout_url") or gp_data.get("payment_url")
        if not checkout_url:
            payment.status = Payment.Status.FAILED
            payment.save(update_fields=["status"])
            return JsonResponse({"detail": "Erreur du service de paiement. Réessayez."}, status=502)

    except Exception as exc:
        logger.exception("api_mobile_initiate_payment error: %s", exc)
        payment.status = Payment.Status.FAILED
        payment.save(update_fields=["status"])
        return JsonResponse({"detail": "Impossible de contacter le service de paiement."}, status=502)

    # Enregistrer l'usage du code promo
    if promo_code and discount_fcfa > 0:
        PromoCodeUsage.objects.get_or_create(
            code=promo_code,
            user=request.api_user,
            defaults={"ad": ad, "discount_applied": discount_fcfa},
        )

    return JsonResponse({
        "checkout_url": checkout_url,
        "deposit_id": str(payment.deposit_id),
        "amount": payment.amount,
        "original_amount": original_amount,
        "discount_fcfa": discount_fcfa,
        "forfait": forfait,
    }, status=201)


@csrf_exempt
@require_http_methods(["GET"])
@require_auth
def api_mobile_payment_status(request, deposit_id):
    """Retourne le statut d'un paiement mobile. Consulte GeniusPay si toujours PENDING."""
    from payments.models import Payment
    from payments import geniuspay as gp_svc

    try:
        payment = Payment.objects.select_related("ad").get(
            deposit_id=deposit_id, user=request.api_user
        )
    except Payment.DoesNotExist:
        return JsonResponse({"detail": "Paiement introuvable."}, status=404)

    if payment.status == Payment.Status.PENDING and payment.geniuspay_reference:
        try:
            gp_data = gp_svc.get_payment(payment.geniuspay_reference)
            gp_status = (gp_data.get("status") or "").lower()
            if gp_status == "completed":
                from payments.views import _activate_ad_for_payment
                _activate_ad_for_payment(payment)
                payment.refresh_from_db()
            elif gp_status in ("failed", "cancelled", "expired"):
                payment.status = Payment.Status.FAILED
                payment.save(update_fields=["status"])
        except Exception as exc:
            logger.warning("api_mobile_payment_status polling error: %s", exc)

    return JsonResponse({
        "status": payment.status,
        "ad_id": payment.ad_id,
        "ad_slug": payment.ad.slug if payment.ad else None,
    })


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
