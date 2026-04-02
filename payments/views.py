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
from .models import Payment
from . import geniuspay as geniuspay_svc

logger = logging.getLogger(__name__)

# ─── Tarifs ───────────────────────────────────────────────────────────────────
PRICE_STANDARD = 600    # FCFA — annonce 5 jours
PRICE_BOOST    = 1100   # FCFA — boost tête de liste 2h/jour (sur annonce existante)
PRICE_BUNDLE   = 1500   # FCFA — standard + boost en une seule transaction
PRICE_RENEWAL  = 600    # FCFA — renouvellement (+5 jours)


# ─── Helpers ──────────────────────────────────────────────────────────────────

def _build_return_url(request: HttpRequest, deposit_id) -> tuple[str, str]:
    """Retourne (success_url, error_url) pour GeniusPay."""
    base = request.build_absolute_uri(
        reverse("payments:return", kwargs={"deposit_id": str(deposit_id)})
    )
    return base, base + "?failed=1"


def _call_geniuspay(request: HttpRequest, payment: Payment, description: str) -> str | None:
    """
    Initie le paiement GeniusPay, met à jour le Payment et retourne le checkout_url.
    Retourne None en cas d'erreur (le payment est marqué FAILED).
    """
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
            customer_name=request.user.username,
            customer_email=request.user.email or None,
        )
        payment.geniuspay_reference = data.get("reference", "")
        payment.gateway_response = data
        payment.save(update_fields=["geniuspay_reference", "gateway_response"])
        return data.get("checkout_url") or data.get("payment_url")
    except Exception as exc:
        logger.exception("GeniusPay create_payment failed for payment %s: %s", payment.pk, exc)
        payment.status = Payment.Status.FAILED
        payment.save(update_fields=["status"])
        return None


# ─── Formulaire de paiement (après création de l'annonce) ────────────────────

@login_required
def pay_form(request: HttpRequest) -> HttpResponse:
    """Affiche le choix Standard (600) ou Bundle (1 500) pour une annonce en DRAFT."""
    ad_id = request.session.get("pending_ad_id")
    if not ad_id:
        return redirect("post")
    try:
        ad = Ad.objects.get(pk=ad_id, user=request.user, status=Ad.Status.DRAFT)
    except Ad.DoesNotExist:
        return redirect("post")
    return render(request, "payments/pay_form.html", {
        "ad": ad,
        "price_standard": PRICE_STANDARD,
        "price_boost": PRICE_BOOST,
        "price_bundle": PRICE_BUNDLE,
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

@login_required
@require_POST
def initiate_payment(request: HttpRequest) -> HttpResponse:
    """
    Crée un paiement GeniusPay et redirige vers la page de checkout.
    Attendu en session : 'pending_ad_id'.
    Attendu en POST    : 'want_boost' (0 = standard, 1 = bundle).
    """
    ad_id = request.session.pop("pending_ad_id", None)
    if not ad_id:
        return redirect("post")

    try:
        ad = Ad.objects.get(pk=ad_id, user=request.user, status=Ad.Status.DRAFT)
    except Ad.DoesNotExist:
        return redirect("post")

    want_boost = request.POST.get("want_boost") == "1"
    pay_type  = Payment.Type.BUNDLE   if want_boost else Payment.Type.STANDARD
    amount    = PRICE_BUNDLE          if want_boost else PRICE_STANDARD
    desc      = "KIABA Standard+Boost" if want_boost else "KIABA Annonce"

    payment = Payment.objects.create(
        user=request.user,
        ad=ad,
        type=pay_type,
        amount=amount,
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

    # Idempotence : ne rien faire si déjà traité
    if payment.status != Payment.Status.PENDING:
        return HttpResponse("OK", status=200)

    payment.gateway_response = body

    if event == "payment.success" or gp_status == "completed":
        _activate_ad_for_payment(payment)
    elif event in ("payment.failed", "payment.cancelled", "payment.expired") or gp_status in ("failed", "cancelled", "expired"):
        payment.status = Payment.Status.FAILED
        payment.save(update_fields=["status", "gateway_response"])
        logger.info("GeniusPay paiement échoué/annulé: %s (%s)", reference, event)

    return HttpResponse("OK", status=200)


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
    GET  → formulaire de confirmation renouvellement (600 FCFA / +5 jours)
    POST → initie le paiement GeniusPay et redirige vers checkout
    """
    try:
        ad = Ad.objects.get(pk=ad_id, user=request.user)
    except Ad.DoesNotExist:
        messages.error(request, "Annonce introuvable.")
        return redirect("dashboard")

    if request.method == "POST":
        payment = Payment.objects.create(
            user=request.user,
            ad=ad,
            type=Payment.Type.RENEWAL,
            amount=PRICE_RENEWAL,
        )
        checkout_url = _call_geniuspay(request, payment, "KIABA Renouvellement annonce")
        if not checkout_url:
            messages.error(request, "Erreur de connexion au service de paiement. Réessayez.")
            return redirect("dashboard")
        return redirect(checkout_url)

    return render(request, "payments/renew_form.html", {
        "ad": ad,
        "price_renewal": PRICE_RENEWAL,
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

        if payment.type in (Payment.Type.STANDARD, Payment.Type.BUNDLE):
            ad.expires_at = now + timezone.timedelta(days=5)
            if ad.status == Ad.Status.DRAFT:
                ad.status = Ad.Status.PENDING

        if payment.type == Payment.Type.RENEWAL:
            base = ad.expires_at if (ad.expires_at and ad.expires_at > now) else now
            ad.expires_at = base + timezone.timedelta(days=5)
            if ad.status in (Ad.Status.DRAFT, Ad.Status.EXPIRED):
                ad.status = Ad.Status.PENDING

        if payment.type in (Payment.Type.BOOST, Payment.Type.BUNDLE):
            ad.is_boosted      = True
            ad.boost_expires_at = (ad.expires_at or now) + timezone.timedelta(days=0)
            # Monter en tête de liste immédiatement pour 2 heures
            ad.is_premium      = True
            ad.premium_until   = now + timezone.timedelta(hours=2)

        ad.save(update_fields=[
            "status", "expires_at",
            "is_boosted", "boost_expires_at",
            "is_premium", "premium_until",
        ])

        # Déclencher l'approbation automatique pour les nouvelles annonces
        if payment.type in (Payment.Type.STANDARD, Payment.Type.BUNDLE, Payment.Type.RENEWAL):
            try:
                from ads.tasks import auto_approve_ad
                auto_approve_ad.apply_async(args=[ad.id], countdown=10)
            except Exception as exc:
                logger.warning("auto_approve_ad task failed: %s", exc)

        logger.info(
            "Payment %s (%s) COMPLETED → annonce %s status=%s boosted=%s",
            payment.deposit_id, payment.type, ad.pk, ad.status, ad.is_boosted,
        )
