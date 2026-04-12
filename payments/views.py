import json
import logging
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import HttpRequest, HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_GET, require_POST

from ads.models import Ad
from .models import Payment, PromoCodeUsage
from . import geniuspay as geniuspay_svc

def _apply_promo(code: str, user, amount: int) -> tuple[int, int]:
    """
    Retourne (nouveau_montant, réduction_fcfa).
    Lève ValueError si le code est invalide, expiré ou déjà utilisé.
    """
    from .models import PromoCode
    code = code.strip().upper()
    try:
        promo = PromoCode.objects.get(code=code)
    except PromoCode.DoesNotExist:
        raise ValueError("Code promo invalide.")
    if not promo.is_valid():
        raise ValueError("Ce code promo n'est plus valide ou a expiré.")
    if PromoCodeUsage.objects.filter(code=code, user=user).exists():
        raise ValueError("Ce code promo a déjà été utilisé sur votre compte.")
    discount = int(amount * promo.discount_percent / 100)
    return max(amount - discount, 1), discount

logger = logging.getLogger(__name__)

# ─── Tarifs ───────────────────────────────────────────────────────────────────
# Publications initiales
PRICE_STANDARD  = 1000   # FCFA — annonce 5 jours sans boost
PRICE_BOOST     = 800    # FCFA — boost seul sur annonce existante (tête 2h)
PRICE_BUNDLE    = 1800   # FCFA — standard 5j + boost tête 2h
PRICE_FORTNIGHT = 3500   # FCFA — 15 jours + boost tête 4h
PRICE_MONTHLY   = 6500   # FCFA — 30 jours + boost tête 3h
# Renouvellements
PRICE_RENEW_15   = 1000  # FCFA — +15 jours sans boost
PRICE_RENEW_15B  = 2500  # FCFA — +15 jours + boost (1000 + 1500)
PRICE_RENEW_MON  = 2000  # FCFA — +30 jours sans boost
PRICE_RENEW_MONB = 4000  # FCFA — +30 jours + boost (2000 + 2000)

# Intervalle de remontée en tête selon forfait (heures)
BOOST_INTERVAL = {
    Payment.Type.BOOST:      2,
    Payment.Type.BUNDLE:     2,
    Payment.Type.FORTNIGHT:  4,
    Payment.Type.MONTHLY:    3,
    Payment.Type.RENEW_15B:  4,
    Payment.Type.RENEW_MONB: 3,
}


# ─── Helpers ──────────────────────────────────────────────────────────────────

def _build_return_url(request: HttpRequest, deposit_id) -> tuple[str, str]:
    """Retourne (success_url, error_url) pour GeniusPay."""
    base = request.build_absolute_uri(
        reverse("payments:return", kwargs={"deposit_id": str(deposit_id)})
    )
    return base, base + "?failed=1"


def _call_geniuspay(
    request: HttpRequest,
    payment: Payment,
    description: str,
) -> str | None:
    """Initie le paiement GeniusPay et retourne le checkout_url."""
    success_url, error_url = _build_return_url(request, payment.deposit_id)
    try:
        data = geniuspay_svc.create_payment(
            amount=payment.amount,
            description=description,
            success_url=success_url,
            error_url=error_url,
            metadata={
                "deposit_id": str(payment.deposit_id),
                "type": payment.type,
                "ad_id": payment.ad_id,
            },
        )
        payment.geniuspay_reference = data.get("reference", "")
        payment.gateway_response = data
        payment.save(update_fields=["geniuspay_reference", "gateway_response"])
        final_url = data.get("checkout_url") or data.get("payment_url")
        logger.info(
            "GeniusPay paiement initié: user_id=%s ad_id=%s type=%s montant=%s ref=%s",
            payment.user_id, payment.ad_id, payment.type, payment.amount,
            payment.geniuspay_reference,
        )
        return final_url
    except Exception as exc:
        logger.exception("GeniusPay create_payment failed for payment %s: %s", payment.pk, exc)
        payment.status = Payment.Status.FAILED
        payment.save(update_fields=["status"])
        return None


# ─── Formulaire de paiement (après création de l'annonce) ────────────────────

@login_required
def pay_form(request: HttpRequest) -> HttpResponse:
    """Affiche les 4 forfaits de publication pour une annonce en DRAFT."""
    # On lit l'ad_id sans le supprimer de la session ici : c'est initiate_payment
    # qui fait le pop() définitif. Conserver en session permet de recharger la page
    # sans perdre le contexte, mais on valide toujours que l'annonce appartient
    # à l'utilisateur courant (pas de fixation de session cross-user possible).
    ad_id = request.session.get("pending_ad_id")
    if not ad_id:
        return redirect("post")
    try:
        ad = Ad.objects.get(pk=ad_id, user=request.user, status=Ad.Status.DRAFT)
    except Ad.DoesNotExist:
        # L'annonce n'appartient pas à cet utilisateur ou n'est plus DRAFT
        request.session.pop("pending_ad_id", None)
        return redirect("post")
    return render(request, "payments/pay_form.html", {
        "ad": ad,
        "price_standard":  PRICE_STANDARD,
        "price_boost":     PRICE_BOOST,
        "price_bundle":    PRICE_BUNDLE,
        "price_fortnight": PRICE_FORTNIGHT,
        "price_monthly":   PRICE_MONTHLY,
    })


# ─── Relancer le paiement d'une annonce DRAFT depuis le dashboard ─────────────

@login_required
def pay_for_existing_ad(request: HttpRequest, ad_id: int) -> HttpResponse:
    try:
        ad = Ad.objects.get(pk=ad_id, user=request.user, status=Ad.Status.DRAFT)
    except Ad.DoesNotExist:
        messages.error(request, "Annonce introuvable ou déjà payée.")
        return redirect("dashboard")
    request.session["pending_ad_id"] = ad.id
    return redirect("payments:pay_form")


# ─── Initier un paiement (POST depuis le formulaire) ─────────────────────────

def _payment_rate_limited(user_id: int) -> bool:
    """Retourne True si l'utilisateur dépasse 2 initiations de paiement par minute."""
    from django.core.cache import cache
    key = f"pay_ratelimit:{user_id}"
    count = cache.get(key, 0)
    if count >= 2:
        return True
    cache.set(key, count + 1, timeout=60)
    return False


def _status_poll_rate_limited(user_id: int) -> bool:
    """Retourne True si l'utilisateur dépasse 20 polls de statut par minute."""
    from django.core.cache import cache
    key = f"pay_status_ratelimit:{user_id}"
    count = cache.get(key, 0)
    if count >= 20:
        return True
    cache.set(key, count + 1, timeout=60)
    return False


@login_required
@require_POST
def initiate_payment(request: HttpRequest) -> HttpResponse:
    """
    Crée un paiement GeniusPay et redirige vers la page de checkout.
    Attendu en session : 'pending_ad_id'.
    Attendu en POST    : 'forfait' (standard | bundle | fortnight | monthly).
    """
    if _payment_rate_limited(request.user.pk):
        logger.warning("initiate_payment: rate limit atteint pour user %s", request.user.pk)
        messages.error(request, "Trop de tentatives. Attendez une minute avant de réessayer.")
        return redirect("payments:pay_form")

    ad_id = request.session.pop("pending_ad_id", None)
    if not ad_id:
        return redirect("post")

    try:
        ad = Ad.objects.get(pk=ad_id, user=request.user, status=Ad.Status.DRAFT)
    except Ad.DoesNotExist:
        return redirect("post")

    forfait = request.POST.get("forfait", "")
    FORFAIT_MAP = {
        "standard":  (Payment.Type.STANDARD,  PRICE_STANDARD,  "KIABA Annonce 5j"),
        "bundle":    (Payment.Type.BUNDLE,     PRICE_BUNDLE,    "KIABA Annonce 5j + Boost"),
        "fortnight": (Payment.Type.FORTNIGHT,  PRICE_FORTNIGHT, "KIABA Pack 15j + Boost"),
        "monthly":   (Payment.Type.MONTHLY,    PRICE_MONTHLY,   "KIABA Pack mensuel + Boost"),
    }
    if forfait not in FORFAIT_MAP:
        logger.warning("initiate_payment: forfait invalide '%s' pour user %s", forfait, request.user.pk)
        request.session["pending_ad_id"] = ad_id
        messages.error(request, "Forfait invalide. Veuillez choisir une option.")
        return redirect("payments:pay_form")
    pay_type, amount, desc = FORFAIT_MAP[forfait]

    # ── Code promo (optionnel) ─────────────────────────────────────────────
    promo_code = request.POST.get("promo_code", "").strip().upper()
    discount_fcfa = 0
    if promo_code:
        try:
            amount, discount_fcfa = _apply_promo(promo_code, request.user, amount)
        except ValueError as e:
            request.session["pending_ad_id"] = ad_id
            messages.error(request, str(e))
            return redirect("payments:pay_form")

    payment = Payment.objects.create(
        user=request.user,
        ad=ad,
        type=pay_type,
        amount=amount,
    )

    # Enregistrer l'usage du code promo après création du paiement
    if promo_code and discount_fcfa > 0:
        PromoCodeUsage.objects.get_or_create(
            code=promo_code,
            user=request.user,
            defaults={"ad": ad, "discount_applied": discount_fcfa},
        )

    checkout_url = _call_geniuspay(request, payment, desc)
    if not checkout_url:
        # Remettre l'annonce en session pour réessayer
        request.session["pending_ad_id"] = ad_id
        messages.error(request, "Erreur de connexion au service de paiement. Réessayez.")
        return redirect("payments:pay_form")

    return redirect(checkout_url)


# ─── Page de retour (GeniusPay redirige ici après paiement) ──────────────────

@login_required
def payment_return(request: HttpRequest, deposit_id) -> HttpResponse:
    """
    Page affichée après que GeniusPay redirige le client.
    Peut être success_url (?failed absent) ou error_url (?failed=1).
    Le statut réel est confirmé par webhook ; le JS polle /pay/status/<id>/.
    """
    payment = get_object_or_404(Payment, deposit_id=deposit_id, user=request.user)
    forced_failed = request.GET.get("failed") == "1"

    # Si GeniusPay indique explicitement un échec et le paiement est encore PENDING
    if forced_failed and payment.status == Payment.Status.PENDING:
        payment.status = Payment.Status.FAILED
        payment.save(update_fields=["status"])

    return render(request, "payments/return.html", {
        "payment": payment,
        "forced_failed": forced_failed,
    })


# ─── Polling de statut (appelé par le JS de la page de retour) ───────────────

@login_required
@require_GET
def payment_status(request: HttpRequest, deposit_id) -> JsonResponse:
    """Renvoie le statut du paiement ; consulte GeniusPay si toujours PENDING."""
    if _status_poll_rate_limited(request.user.pk):
        return JsonResponse({"error": "too_many_requests"}, status=429)

    payment = get_object_or_404(Payment, deposit_id=deposit_id, user=request.user)

    if payment.status == Payment.Status.PENDING and payment.geniuspay_reference:
        try:
            data = geniuspay_svc.get_payment(payment.geniuspay_reference)
            gp_status = (data.get("status") or "").lower()
            if gp_status == "completed":
                _activate_ad_for_payment(payment)
            elif gp_status in ("failed", "cancelled", "expired"):
                payment.status = Payment.Status.FAILED
                payment.save(update_fields=["status"])
        except Exception as exc:
            logger.warning("GeniusPay get_payment error for %s: %s", deposit_id, exc)

    return JsonResponse({
        "status": payment.status,
        "ad_slug": payment.ad.slug if payment.ad else None,
    })


# ─── Webhook GeniusPay (serveur → serveur) ────────────────────────────────────

@csrf_exempt
@require_POST
def geniuspay_webhook(request: HttpRequest) -> HttpResponse:
    """
    Reçoit les notifications asynchrones de GeniusPay.
    Vérifie la signature HMAC-SHA256 avant tout traitement.
    """
    timestamp = request.headers.get("X-Webhook-Timestamp", "")
    signature = request.headers.get("X-Webhook-Signature", "")
    event     = request.headers.get("X-Webhook-Event", "")

    if not geniuspay_svc.verify_webhook_signature(timestamp, request.body, signature):
        logger.warning("GeniusPay webhook: signature invalide")
        return HttpResponse("Unauthorized", status=401)

    try:
        body = json.loads(request.body)
    except json.JSONDecodeError:
        return HttpResponse("Bad Request", status=400)

    data       = body.get("data", {})
    reference  = data.get("reference", "")
    gp_status  = (data.get("status") or "").lower()

    logger.info("GeniusPay webhook: event=%s reference=%s status=%s", event, reference, gp_status)

    if not reference:
        return HttpResponse("OK", status=200)

    from django.db import transaction

    # Retrouver le Payment via la référence GeniusPay
    try:
        payment = Payment.objects.get(geniuspay_reference=reference)
    except Payment.DoesNotExist:
        # Peut arriver si le webhook arrive avant la sauvegarde (race condition rare)
        # Essayer via les métadonnées
        deposit_id = (data.get("metadata") or {}).get("deposit_id")
        if deposit_id:
            try:
                payment = Payment.objects.get(deposit_id=deposit_id)
                # Mettre à jour la référence manquante
                if not payment.geniuspay_reference:
                    payment.geniuspay_reference = reference
                    payment.save(update_fields=["geniuspay_reference"])
            except Payment.DoesNotExist:
                logger.warning("GeniusPay webhook: paiement introuvable (ref=%s, deposit=%s)", reference, deposit_id)
                return HttpResponse("OK", status=200)
        else:
            logger.warning("GeniusPay webhook: référence inconnue %s", reference)
            return HttpResponse("OK", status=200)

    # Idempotence avec lock pour éviter les double-traitements (webhooks dupliqués).
    # select_for_update() garantit qu'un seul thread traite le paiement à la fois ;
    # le second verra le statut déjà mis à jour et sortira immédiatement.
    with transaction.atomic():
        payment = Payment.objects.select_for_update().get(pk=payment.pk)
        if payment.status != Payment.Status.PENDING:
            logger.info(
                "GeniusPay webhook rejeu ignoré: ref=%s statut_actuel=%s",
                reference, payment.status,
            )
            return HttpResponse("OK", status=200)

        payment.gateway_response = body

        if event == "payment.success" or gp_status == "completed":
            # Vérifier que le montant payé correspond au montant attendu
            paid_amount = data.get("amount")
            if paid_amount is not None:
                try:
                    paid_int = int(float(paid_amount))
                except (ValueError, TypeError):
                    paid_int = 0
                if paid_int < payment.amount:
                    logger.error(
                        "GeniusPay webhook: montant insuffisant ref=%s payé=%s attendu=%s — rejeté",
                        reference, paid_amount, payment.amount,
                    )
                    payment.status = Payment.Status.FAILED
                    payment.save(update_fields=["status", "gateway_response"])
                    return HttpResponse("OK", status=200)
            _activate_ad_for_payment(payment)
        elif event in ("payment.failed", "payment.cancelled", "payment.expired") or gp_status in ("failed", "cancelled", "expired"):
            payment.status = Payment.Status.FAILED
            payment.save(update_fields=["status", "gateway_response"])
            logger.info("GeniusPay paiement échoué/annulé: %s (%s)", reference, event)

    return HttpResponse("OK", status=200)


# ─── Validation AJAX du code promo ───────────────────────────────────────────

@login_required
@require_POST
def check_promo_code(request: HttpRequest) -> JsonResponse:
    """Valide un code promo et retourne la réduction applicable."""
    code = request.POST.get("code", "").strip().upper()
    forfait = request.POST.get("forfait", "standard")

    FORFAIT_PRICES = {
        "standard":  PRICE_STANDARD,
        "bundle":    PRICE_BUNDLE,
        "fortnight": PRICE_FORTNIGHT,
        "monthly":   PRICE_MONTHLY,
    }
    amount = FORFAIT_PRICES.get(forfait, PRICE_STANDARD)

    try:
        from .models import PromoCode
        promo = PromoCode.objects.get(code=code)
        new_amount, discount = _apply_promo(code, request.user, amount)
        return JsonResponse({
            "valid": True,
            "discount_pct": promo.discount_percent,
            "discount_fcfa": discount,
            "new_amount": new_amount,
            "original_amount": amount,
        })
    except PromoCode.DoesNotExist:
        return JsonResponse({"valid": False, "error": "Code promo invalide."})
    except ValueError as e:
        return JsonResponse({"valid": False, "error": str(e)})


# ─── Booster une annonce existante ────────────────────────────────────────────

@login_required
def boost_ad(request: HttpRequest, ad_id: int) -> HttpResponse:
    """
    GET  → formulaire de confirmation boost (1 100 FCFA)
    POST → initie le paiement GeniusPay et redirige vers checkout
    """
    try:
        ad = Ad.objects.get(pk=ad_id, user=request.user)
    except Ad.DoesNotExist:
        messages.error(request, "Annonce introuvable.")
        return redirect("dashboard")

    if ad.is_boosted and ad.boost_expires_at and ad.boost_expires_at > timezone.now():
        messages.info(request, "Cette annonce est déjà boostée.")
        return redirect("dashboard")

    if request.method == "POST":
        payment = Payment.objects.create(
            user=request.user,
            ad=ad,
            type=Payment.Type.BOOST,
            amount=PRICE_BOOST,
        )
        checkout_url = _call_geniuspay(request, payment, "KIABA Boost annonce")
        if not checkout_url:
            messages.error(request, "Erreur de connexion au service de paiement. Réessayez.")
            return redirect("dashboard")
        return redirect(checkout_url)

    return render(request, "payments/boost_form.html", {
        "ad": ad,
        "price_boost": PRICE_BOOST,
    })


# ─── Renouveler une annonce existante ────────────────────────────────────────

@login_required
def renew_ad(request: HttpRequest, ad_id: int) -> HttpResponse:
    """
    GET  → formulaire avec 4 options de renouvellement
    POST → initie le paiement GeniusPay (forfait choisi via POST 'forfait')
    """
    try:
        ad = Ad.objects.get(pk=ad_id, user=request.user)
    except Ad.DoesNotExist:
        messages.error(request, "Annonce introuvable.")
        return redirect("dashboard")

    if request.method == "POST":
        forfait = request.POST.get("forfait", "")
        RENEW_MAP = {
            "renew_15":   (Payment.Type.RENEW_15,   PRICE_RENEW_15,   "KIABA Renouvellement 15j"),
            "renew_15b":  (Payment.Type.RENEW_15B,  PRICE_RENEW_15B,  "KIABA Renouvellement 15j + Boost"),
            "renew_mon":  (Payment.Type.RENEW_MON,  PRICE_RENEW_MON,  "KIABA Renouvellement 1 mois"),
            "renew_monb": (Payment.Type.RENEW_MONB, PRICE_RENEW_MONB, "KIABA Renouvellement 1 mois + Boost"),
        }
        if forfait not in RENEW_MAP:
            logger.warning("renew_ad: forfait invalide '%s' pour user %s", forfait, request.user.pk)
            messages.error(request, "Forfait invalide. Veuillez choisir une option.")
            return redirect("payments:renew_ad", ad_id=ad_id)
        pay_type, amount, desc = RENEW_MAP[forfait]
        payment = Payment.objects.create(
            user=request.user,
            ad=ad,
            type=pay_type,
            amount=amount,
        )
        checkout_url = _call_geniuspay(request, payment, desc)
        if not checkout_url:
            messages.error(request, "Erreur de connexion au service de paiement. Réessayez.")
            return redirect("dashboard")
        return redirect(checkout_url)

    return render(request, "payments/renew_form.html", {
        "ad": ad,
        "price_renew_15":   PRICE_RENEW_15,
        "price_renew_15b":  PRICE_RENEW_15B,
        "price_renew_mon":  PRICE_RENEW_MON,
        "price_renew_monb": PRICE_RENEW_MONB,
    })


# ─── Activation de l'annonce après paiement confirmé ─────────────────────────

def _activate_ad_for_payment(payment: Payment) -> None:
    """
    Active ou booste l'annonce suite à un paiement COMPLETED.
    Exécuté atomiquement pour éviter les doubles traitements.

    Types :
      STANDARD → annonce 5 jours, status DRAFT → PENDING → auto-approuvée
      BOOST    → is_boosted=True, fenêtre premium 2h immédiate
      BUNDLE   → standard + boost combinés
    """
    from django.db import transaction

    now = timezone.now()

    with transaction.atomic():
        payment = Payment.objects.select_for_update().get(pk=payment.pk)
        if payment.status != Payment.Status.PENDING:
            return  # Déjà traité (idempotence)

        payment.status = Payment.Status.COMPLETED
        payment.completed_at = now
        payment.save(update_fields=["status", "completed_at", "gateway_response"])

        ad = payment.ad
        if not ad:
            return

        T = Payment.Type

        # ── Durée selon forfait ───────────────────────────────────────────
        DURATION = {
            T.STANDARD:   5,
            T.BUNDLE:     5,
            T.FORTNIGHT:  15,
            T.MONTHLY:    30,
        }
        RENEWAL_DURATION = {
            T.RENEW_15:   15,
            T.RENEW_15B:  15,
            T.RENEW_MON:  30,
            T.RENEW_MONB: 30,
        }

        if payment.type in DURATION:
            ad.expires_at = now + timezone.timedelta(days=DURATION[payment.type])
            if ad.status == Ad.Status.DRAFT:
                ad.status = Ad.Status.PENDING

        if payment.type in RENEWAL_DURATION:
            base = ad.expires_at if (ad.expires_at and ad.expires_at > now) else now
            ad.expires_at = base + timezone.timedelta(days=RENEWAL_DURATION[payment.type])
            if ad.status in (Ad.Status.DRAFT, Ad.Status.ARCHIVED):
                ad.status = Ad.Status.PENDING

        # ── Boost selon forfait ───────────────────────────────────────────
        BOOSTED_TYPES = (T.BOOST, T.BUNDLE, T.FORTNIGHT, T.MONTHLY, T.RENEW_15B, T.RENEW_MONB)
        if payment.type in BOOSTED_TYPES:
            interval = BOOST_INTERVAL.get(payment.type, 2)
            ad.is_boosted        = True
            ad.boost_expires_at  = ad.expires_at or now
            ad.boost_interval_hours = interval
            # Monter immédiatement en tête pour X heures
            ad.is_premium        = True
            ad.premium_until     = now + timezone.timedelta(hours=interval)

        ad.save(update_fields=[
            "status", "expires_at",
            "is_boosted", "boost_expires_at", "boost_interval_hours",
            "is_premium", "premium_until",
        ])

        # Approbation automatique des nouvelles annonces
        NEW_AD_TYPES = (T.STANDARD, T.BUNDLE, T.FORTNIGHT, T.MONTHLY,
                        T.RENEW_15, T.RENEW_15B, T.RENEW_MON, T.RENEW_MONB)
        if payment.type in NEW_AD_TYPES:
            try:
                from ads.tasks import auto_approve_ad
                auto_approve_ad.apply_async(args=[ad.id], countdown=10)
            except Exception as exc:
                logger.warning("auto_approve_ad task failed: %s", exc)

        logger.info(
            "Payment %s (%s) COMPLETED → annonce %s status=%s boosted=%s interval=%sh",
            payment.deposit_id, payment.type, ad.pk, ad.status,
            ad.is_boosted, getattr(ad, "boost_interval_hours", 2),
        )


@login_required
@require_GET
def payment_history(request: HttpRequest) -> HttpResponse:
    """Historique des paiements de l'utilisateur connecté."""
    from django.core.paginator import Paginator
    payments = (
        Payment.objects.filter(user=request.user)
        .select_related("ad")
        .order_by("-created_at")
    )
    paginator = Paginator(payments, 20)
    page_obj = paginator.get_page(request.GET.get("page", "1"))
    return render(request, "payments/history.html", {
        "page_obj": page_obj,
        "is_paginated": page_obj.has_other_pages(),
    })
