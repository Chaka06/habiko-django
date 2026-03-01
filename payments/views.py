import json
import logging
from django.contrib.auth.decorators import login_required
from django.http import HttpRequest, HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_GET, require_POST
from django.utils import timezone

from ads.models import Ad
from .models import Payment
from . import pawapay as pawapay_svc

logger = logging.getLogger(__name__)

# ─── Tarifs ───────────────────────────────────────────────────────────────────
PRICE_STANDARD = 500   # FCFA — annonce 5 jours
PRICE_BOOST = 700      # FCFA — boost en tête de liste 2h/jour pendant 7 jours (en plus du standard)


# ─── 0b. Relancer le paiement pour une annonce DRAFT depuis le dashboard ──────

@login_required
def pay_for_existing_ad(request: HttpRequest, ad_id: int) -> HttpResponse:
    """Repositionne l'ad_id en session puis redirige vers le formulaire de paiement."""
    try:
        ad = Ad.objects.get(pk=ad_id, user=request.user, status=Ad.Status.DRAFT)
    except Ad.DoesNotExist:
        from django.contrib import messages
        messages.error(request, "Annonce introuvable ou déjà payée.")
        return redirect("dashboard")
    request.session["pending_ad_id"] = ad.id
    return redirect("payments:pay_form")


# ─── 0. Formulaire de paiement (affiché après la création de l'annonce) ──────

@login_required
def pay_form(request: HttpRequest) -> HttpResponse:
    """
    Affiche le formulaire de choix d'opérateur + option boost
    après la création de l'annonce (ad_id stocké en session).
    """
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
        "price_total_boost": PRICE_STANDARD + PRICE_BOOST,
        "correspondents": pawapay_svc.CORRESPONDENTS,
    })


# ─── 1. Initier un paiement standard (appelé depuis la vue post) ───────────────

@login_required
@require_POST
def initiate_payment(request: HttpRequest) -> HttpResponse:
    """
    Initie un paiement PawaPay après la création d'une annonce en DRAFT.
    Attendu en session : 'pending_ad_id' (id de l'annonce fraîchement créée).
    """
    ad_id = request.session.pop("pending_ad_id", None)
    if not ad_id:
        return redirect("post")

    try:
        ad = Ad.objects.get(pk=ad_id, user=request.user, status=Ad.Status.DRAFT)
    except Ad.DoesNotExist:
        return redirect("post")

    phone = (request.POST.get("pay_phone") or "").strip().replace("+", "").replace(" ", "")
    correspondent = (request.POST.get("pay_correspondent") or "").strip()
    want_boost = request.POST.get("want_boost") == "1"

    if not phone or correspondent not in pawapay_svc.CORRESPONDENTS:
        return render(request, "payments/pay_form.html", {
            "ad": ad,
            "error": "Numéro de téléphone ou opérateur invalide.",
            "price_standard": PRICE_STANDARD,
            "price_boost": PRICE_BOOST,
            "correspondents": pawapay_svc.CORRESPONDENTS,
        })

    # URLs de retour pour les opérateurs REDIRECT_AUTH (Wave)
    is_redirect = correspondent in pawapay_svc.REDIRECT_AUTH_PROVIDERS

    # 1re passe : paiement STANDARD
    std_payment = Payment.objects.create(
        user=request.user,
        ad=ad,
        type=Payment.Type.STANDARD,
        amount=PRICE_STANDARD,
        phone=phone,
        correspondent=correspondent,
    )
    try:
        from django.urls import reverse
        waiting_url = request.build_absolute_uri(
            reverse("payments:waiting", kwargs={"deposit_id": str(std_payment.deposit_id)})
        )
        resp = pawapay_svc.initiate_deposit(
            deposit_id=str(std_payment.deposit_id),
            amount=PRICE_STANDARD,
            phone=phone,
            correspondent=correspondent,
            description="KIABA annonce",
            successful_url=waiting_url if is_redirect else None,
            failed_url=request.build_absolute_uri(reverse("dashboard")) if is_redirect else None,
        )
        std_payment.pawapay_response = resp
        std_payment.save(update_fields=["pawapay_response"])
    except Exception as exc:
        logger.exception("PawaPay initiate_deposit failed for payment %s: %s", std_payment.pk, exc)
        std_payment.status = Payment.Status.FAILED
        std_payment.save(update_fields=["status"])
        return render(request, "payments/pay_form.html", {
            "ad": ad,
            "error": "Erreur de connexion au service de paiement. Réessayez.",
            "price_standard": PRICE_STANDARD,
            "price_boost": PRICE_BOOST,
            "correspondents": pawapay_svc.CORRESPONDENTS,
        })

    if want_boost:
        boost_payment = Payment.objects.create(
            user=request.user,
            ad=ad,
            type=Payment.Type.BOOST,
            amount=PRICE_BOOST,
            phone=phone,
            correspondent=correspondent,
        )
        try:
            resp_b = pawapay_svc.initiate_deposit(
                deposit_id=str(boost_payment.deposit_id),
                amount=PRICE_BOOST,
                phone=phone,
                correspondent=correspondent,
                description="KIABA boost",
            )
            boost_payment.pawapay_response = resp_b
            boost_payment.save(update_fields=["pawapay_response"])
        except Exception as exc:
            logger.exception("PawaPay boost deposit failed for payment %s: %s", boost_payment.pk, exc)
            boost_payment.status = Payment.Status.FAILED
            boost_payment.save(update_fields=["status"])
            # On continue quand même : l'annonce sera activée sans boost si le std réussit

    # Stocker le deposit_id standard en session pour la page d'attente
    request.session["waiting_deposit_id"] = str(std_payment.deposit_id)
    return redirect("payments:waiting", deposit_id=std_payment.deposit_id)


# ─── 2. Page d'attente ─────────────────────────────────────────────────────────

@login_required
def payment_waiting(request: HttpRequest, deposit_id) -> HttpResponse:
    payment = get_object_or_404(Payment, deposit_id=deposit_id, user=request.user)
    return render(request, "payments/waiting.html", {
        "payment": payment,
        "price_standard": PRICE_STANDARD,
        "price_boost": PRICE_BOOST,
    })


# ─── 3. Polling de statut (appelé par le JS de la page d'attente) ──────────────

@login_required
@require_GET
def payment_status(request: HttpRequest, deposit_id) -> JsonResponse:
    """Renvoie le statut du paiement (consulte PawaPay si encore PENDING)."""
    payment = get_object_or_404(Payment, deposit_id=deposit_id, user=request.user)

    auth_url = None
    if payment.status == Payment.Status.PENDING:
        try:
            data = pawapay_svc.check_deposit(str(deposit_id))
            remote_status = (data.get("status") or "").upper()
            if remote_status == "COMPLETED":
                _activate_ad_for_payment(payment)
            elif remote_status == "FAILED":
                payment.status = Payment.Status.FAILED
                payment.save(update_fields=["status"])
            # Pour Wave (REDIRECT_AUTH) : récupérer l'URL d'autorisation
            auth_url = data.get("authorizationUrl")
        except Exception as exc:
            logger.warning("PawaPay check_deposit error for %s: %s", deposit_id, exc)

    return JsonResponse({
        "status": payment.status,
        "ad_slug": payment.ad.slug if payment.ad else None,
        "auth_url": auth_url,
    })


# ─── 4. Webhook PawaPay (callback serveur-à-serveur) ──────────────────────────

@csrf_exempt
@require_POST
def pawapay_webhook(request: HttpRequest) -> HttpResponse:
    """
    Reçoit les notifications asynchrones de PawaPay.
    PawaPay envoie un POST JSON avec le résultat final du dépôt.
    IPs sandbox : 3.64.89.224/32 — vérification IP à activer en production.
    """
    try:
        data = json.loads(request.body)
    except json.JSONDecodeError:
        return HttpResponse("Bad Request", status=400)

    deposit_id = data.get("depositId")
    status = (data.get("status") or "").upper()

    if not deposit_id:
        return HttpResponse("OK", status=200)

    try:
        payment = Payment.objects.get(deposit_id=deposit_id)
    except Payment.DoesNotExist:
        logger.warning("PawaPay webhook: unknown depositId %s", deposit_id)
        return HttpResponse("OK", status=200)

    # Idempotence : ne rien faire si déjà traité
    if payment.status != Payment.Status.PENDING:
        return HttpResponse("OK", status=200)

    payment.pawapay_response = data

    if status == "COMPLETED":
        _activate_ad_for_payment(payment)
    elif status == "FAILED":
        payment.status = Payment.Status.FAILED
        payment.save(update_fields=["status", "pawapay_response"])
        logger.info("PawaPay deposit FAILED for payment %s", payment.pk)

    return HttpResponse("OK", status=200)


# ─── 5. Booster une annonce existante (depuis le dashboard) ───────────────────

@login_required
def boost_ad(request: HttpRequest, ad_id: int) -> HttpResponse:
    """
    Page + traitement pour booster une annonce standard déjà payée.
    GET  → formulaire de paiement boost
    POST → initie le paiement boost PawaPay
    """
    try:
        ad = Ad.objects.get(pk=ad_id, user=request.user)
    except Ad.DoesNotExist:
        from django.contrib import messages
        messages.error(request, "Annonce introuvable.")
        return redirect("dashboard")

    # Vérifier que l'annonce n'est pas déjà boostée et active
    if ad.is_boosted and ad.boost_expires_at and ad.boost_expires_at > timezone.now():
        from django.contrib import messages
        messages.info(request, "Cette annonce est déjà boostée.")
        return redirect("dashboard")

    if request.method == "POST":
        phone = (request.POST.get("pay_phone") or "").strip().replace("+", "").replace(" ", "")
        correspondent = (request.POST.get("pay_correspondent") or "").strip()

        if not phone or correspondent not in pawapay_svc.CORRESPONDENTS:
            return render(request, "payments/boost_form.html", {
                "ad": ad,
                "error": "Numéro de téléphone ou opérateur invalide.",
                "price_boost": PRICE_BOOST,
                "correspondents": pawapay_svc.CORRESPONDENTS,
            })

        payment = Payment.objects.create(
            user=request.user,
            ad=ad,
            type=Payment.Type.BOOST,
            amount=PRICE_BOOST,
            phone=phone,
            correspondent=correspondent,
        )
        try:
            resp = pawapay_svc.initiate_deposit(
                deposit_id=str(payment.deposit_id),
                amount=PRICE_BOOST,
                phone=phone,
                correspondent=correspondent,
                description="KIABA boost",
            )
            payment.pawapay_response = resp
            payment.save(update_fields=["pawapay_response"])
        except Exception as exc:
            logger.exception("PawaPay boost deposit failed: %s", exc)
            payment.status = Payment.Status.FAILED
            payment.save(update_fields=["status"])
            return render(request, "payments/boost_form.html", {
                "ad": ad,
                "error": "Erreur de connexion au service de paiement. Réessayez.",
                "price_boost": PRICE_BOOST,
                "correspondents": pawapay_svc.CORRESPONDENTS,
            })

        return redirect("payments:waiting", deposit_id=payment.deposit_id)

    return render(request, "payments/boost_form.html", {
        "ad": ad,
        "price_boost": PRICE_BOOST,
        "correspondents": pawapay_svc.CORRESPONDENTS,
    })


# ─── Activation de l'annonce après paiement confirmé ─────────────────────────

def _activate_ad_for_payment(payment: Payment) -> None:
    """
    Active ou booste l'annonce suite à un paiement COMPLETED.
    Mis à jour atomiquement pour éviter les doubles activations.
    """
    from django.db import transaction

    now = timezone.now()

    with transaction.atomic():
        # Recharger le payment pour éviter les conditions de course
        payment = Payment.objects.select_for_update().get(pk=payment.pk)
        if payment.status != Payment.Status.PENDING:
            return  # Déjà traité

        payment.status = Payment.Status.COMPLETED
        payment.completed_at = now
        payment.save(update_fields=["status", "completed_at", "pawapay_response"])

        ad = payment.ad
        if not ad:
            return

        if payment.type == Payment.Type.STANDARD:
            # Activer l'annonce + durée de vie 5 jours
            ad.expires_at = now + timezone.timedelta(days=5)
            if ad.status == Ad.Status.DRAFT:
                ad.status = Ad.Status.PENDING  # → sera approuvée par auto_approve
            ad.save(update_fields=["expires_at", "status"])

            # Déclencher l'approbation automatique (10 secondes de délai)
            try:
                from ads.tasks import auto_approve_ad
                auto_approve_ad.apply_async(args=[ad.id], countdown=10)
            except Exception as exc:
                logger.warning("auto_approve_ad task failed: %s", exc)

        elif payment.type == Payment.Type.BOOST:
            # Étendre la durée de vie à 7 jours depuis maintenant (si plus récente)
            boost_expires = now + timezone.timedelta(days=7)
            ad.is_boosted = True
            ad.boost_expires_at = boost_expires
            # Appliquer le premium immédiatement pour 2h
            ad.is_premium = True
            ad.premium_until = now + timezone.timedelta(hours=2)
            # Étendre expires_at si nécessaire
            if not ad.expires_at or ad.expires_at < boost_expires:
                ad.expires_at = boost_expires
            ad.save(update_fields=["is_boosted", "boost_expires_at", "is_premium", "premium_until", "expires_at"])

        logger.info(
            "Payment %s (%s) COMPLETED → ad %s status=%s",
            payment.deposit_id, payment.type, ad.pk, ad.status,
        )
