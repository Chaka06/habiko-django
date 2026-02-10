from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.contrib.auth import update_session_auth_hash
from django.http import HttpRequest, HttpResponse, JsonResponse
from .models import Profile, Account, RechargePackage, BoostOption, Transaction, CustomUser
from .forms import (
    ProfileEditForm,
    CustomPasswordChangeForm,
    PasswordChangeOTPRequestForm,
    RechargeForm,
    BoostForm,
)
from .services import AccountService, BoostService
from .cinetpay import CinetPayService
from .tasks import send_profile_validation_email, send_password_change_email
from .models import EmailOTP
from ads.models import Ad
from django.core.exceptions import ValidationError


@login_required
def profile_edit(request: HttpRequest) -> HttpResponse:
    """Page de modification du profil utilisateur"""
    try:
        profile = request.user.profile
    except Profile.DoesNotExist:
        profile = Profile.objects.create(user=request.user)

    if request.method == "POST":
        form = ProfileEditForm(request.POST, request.FILES, instance=profile)
        if form.is_valid():
            # Sauvegarder le profil (sans commit pour enrichir avant)
            profile = form.save(commit=False)
            # Gérer contact_prefs manuellement
            profile.contact_prefs = form.cleaned_data.get("contact_prefs", [])
            # Sauvegarder WhatsApp dans le profil
            if form.cleaned_data.get("whatsapp_e164"):
                profile.whatsapp_e164 = form.cleaned_data["whatsapp_e164"]
            profile.save()

            # Sauvegarder le numéro de téléphone dans l'utilisateur
            if form.cleaned_data.get("phone_e164"):
                request.user.phone_e164 = form.cleaned_data["phone_e164"]
                request.user.save()

            # Envoyer un email de validation / mise à jour de profil
            send_profile_validation_email.delay(profile.id)

            messages.success(request, "Profil mis à jour avec succès !")
            return redirect("/dashboard/")
    else:
        form = ProfileEditForm(instance=profile)
        # Pré-remplir le numéro de téléphone depuis l'utilisateur
        form.fields["phone_e164"].initial = request.user.phone_e164

    return render(request, "accounts/profile_edit.html", {"form": form})


@login_required
def password_change(request: HttpRequest) -> HttpResponse:
    """Modification du mot de passe en 2 étapes: 1) vérif ancien/nouveau; 2) OTP email."""
    # Étape 2 sera gérée sur une page dédiée

    # Étape 1: valider ancien/nouveau, puis envoyer un code OTP et demander le code
    if request.method == "POST":
        form = CustomPasswordChangeForm(request.user, request.POST)
        if form.is_valid():
            # Stocker le nouveau mot de passe en session (temporaire) et envoyer OTP
            cleaned = form.cleaned_data
            request.session["pending_pwd_change"] = {
                "new_password1": cleaned.get("new_password1"),
            }

            req_form = PasswordChangeOTPRequestForm(user=request.user)
            otp = req_form.save()

            from django.core.mail import send_mail
            from django.conf import settings

            # Utiliser le nouveau service d'email avec template
            from .email_service import EmailService
            from django.conf import settings
            EmailService.send_email(
                subject="Code de confirmation pour changement de mot de passe - KIABA Rencontres",
                to_emails=[request.user.email],
                template_name="account/email/password_change_otp",
                context={
                    "user": request.user,
                    "code": otp.code,
                    "site_url": getattr(settings, "SITE_URL", "https://ci-kiaba.com"),
                },
                fail_silently=False,
            )
            # Log dev
            print(f"[OTP] Password change code for user {request.user.id}: {otp.code}")
            messages.info(
                request, "Code envoyé par email. Saisissez-le pour confirmer le changement."
            )
            return redirect("accounts:password_change_confirm")
    else:
        form = CustomPasswordChangeForm(request.user)

    return render(request, "accounts/password_change.html", {"form": form})


@login_required
def password_change_confirm(request: HttpRequest) -> HttpResponse:
    if not request.session.get("pending_pwd_change"):
        messages.warning(request, "Session expirée. Recommencez la modification du mot de passe.")
        return redirect("accounts:password_change")

    if request.method == "POST":
        code = (request.POST.get("code") or "").strip()
        pending = request.session.get("pending_pwd_change")
        otp = (
            EmailOTP.objects.filter(
                user=request.user,
                purpose=EmailOTP.Purpose.PASSWORD_CHANGE,
                is_used=False,
            )
            .order_by("-created_at")
            .first()
        )
        if not otp or not otp.is_valid(code):
            messages.error(request, "Code OTP incorrect ou expiré")
            return render(request, "accounts/password_change_confirm.html")

        new_password = pending.get("new_password1")
        request.user.set_password(new_password)
        request.user.save()
        otp.is_used = True
        otp.save(update_fields=["is_used"])
        request.session.pop("pending_pwd_change", None)

        update_session_auth_hash(request, request.user)
        send_password_change_email.delay(request.user.id)
        messages.success(request, "Mot de passe modifié avec succès !")
        return redirect("/dashboard/")

    return render(request, "accounts/password_change_confirm.html")


@login_required
def resend_password_change_code(request: HttpRequest) -> HttpResponse:
    if request.method == "POST":
        req_form = PasswordChangeOTPRequestForm(request.POST or None, user=request.user)
        otp = req_form.save()
        
        # Utiliser le nouveau service d'email avec template
        from .email_service import EmailService
        from django.conf import settings
        EmailService.send_email(
            subject="Code de confirmation pour changement de mot de passe - KIABA Rencontres",
            to_emails=[request.user.email],
            template_name="account/email/password_change_otp",
            context={
                "user": request.user,
                "code": otp.code,
                "site_url": getattr(settings, "SITE_URL", "https://ci-kiaba.com"),
            },
            fail_silently=False,
        )
        messages.info(request, "Nouveau code envoyé par email.")
    return redirect("accounts:password_change_confirm")


def resend_verification_email(request: HttpRequest) -> HttpResponse:
    """
    Renvoie l'email de confirmation depuis la page « Vérifiez votre adresse e-mail »
    (après inscription). Utilise le login en attente dans la session (allauth),
    sans exiger d'être connecté. Si la session a expiré, redirige vers la connexion.
    """
    if request.method != "POST":
        return redirect("account_email_verification_sent")

    try:
        from allauth.account.internal.stagekit import unstash_login
        from allauth.account.internal.flows.email_verification import (
            get_address_for_login,
            send_verification_email_to_address,
        )
    except ImportError:
        messages.warning(request, "Impossible de renvoyer l'email. Réessayez plus tard.")
        return redirect("account_login")

    login = unstash_login(request, peek=True)
    if not login or not getattr(login, "user", None) or not login.user:
        messages.info(
            request,
            "Votre session a expiré. Connectez-vous ou inscrivez-vous à nouveau pour recevoir un nouvel email.",
        )
        return redirect("account_login")

    address = get_address_for_login(login)
    if not address or address.verified:
        messages.info(request, "Cet email est déjà vérifié ou la session a expiré.")
        return redirect("account_email_verification_sent")

    sent = send_verification_email_to_address(request, address, signup=True)
    if sent:
        messages.success(request, "Un nouvel email de confirmation a été envoyé. Vérifiez votre boîte de réception.")
    else:
        messages.warning(
            request,
            "Envoi limité pour éviter le spam. Réessayez dans quelques minutes ou vérifiez vos spams.",
        )
    return redirect("account_email_verification_sent")


def validate_profile(request: HttpRequest, profile_id: int) -> HttpResponse:
    """Valider un profil via email"""
    profile = get_object_or_404(Profile, id=profile_id)

    # Marquer le profil comme validé
    profile.is_verified = True
    profile.save()

    messages.success(request, f"Profil de {profile.display_name} validé avec succès !")
    return redirect("/dashboard/")


@login_required
def account_balance(request: HttpRequest) -> HttpResponse:
    """Afficher le solde et les crédits du compte"""
    account = AccountService.get_or_create_account(request.user)
    packages = RechargePackage.objects.filter(is_active=True).order_by("amount")
    
    return render(request, "accounts/account_balance.html", {
        "account": account,
        "packages": packages,
    })


def public_profile(request: HttpRequest, username: str) -> HttpResponse:
    """
    Page de profil public d'un utilisateur (accessible depuis une annonce).
    Affiche la photo de profil, le pseudo, la ville et la liste des annonces.
    """
    user = get_object_or_404(CustomUser, username=username)
    try:
        profile = user.profile
    except Profile.DoesNotExist:
        profile = None

    ads = (
        Ad.objects.filter(user=user, status=Ad.Status.APPROVED)
        .order_by("-created_at")
        .prefetch_related("media", "city")
    )

    return render(
        request,
        "accounts/public_profile.html",
        {
            "profile_user": user,
            "profile": profile,
            "ads": ads,
        },
    )


@login_required
def recharge_account(request: HttpRequest) -> HttpResponse:
    """Recharger le compte avec une formule"""
    if request.method == "POST":
        form = RechargeForm(request.POST)
        if form.is_valid():
            package = form.cleaned_data["package"]
            # Créer une transaction en attente
            transaction = Transaction.objects.create(
                user=request.user,
                transaction_type=Transaction.TransactionType.RECHARGE,
                amount=package.amount,
                status=Transaction.Status.PENDING,
                recharge_package=package,
                description=f"Recharge {package.name}",
            )
            
            # Créer le lien de paiement CinetPay
            try:
                payment_url = CinetPayService.create_payment_link(
                    transaction,
                    package.amount,
                    f"Recharge {package.name}"
                )
                # Rediriger vers CinetPay
                return redirect(payment_url)
            except ValueError as e:
                messages.error(request, f"Erreur de paiement: {str(e)}")
                transaction.delete()
                return redirect("accounts:recharge_account")
    else:
        form = RechargeForm()
    
    packages = RechargePackage.objects.filter(is_active=True).order_by("amount")
    return render(request, "accounts/recharge_account.html", {
        "form": form,
        "packages": packages,
    })


@login_required
def boost_ad(request: HttpRequest, ad_id: int) -> HttpResponse:
    """Booster une annonce"""
    ad = get_object_or_404(Ad, id=ad_id, user=request.user)
    account = AccountService.get_or_create_account(request.user)
    
    # Filtrer les options selon le type
    premium_options = BoostOption.objects.filter(
        boost_type=BoostOption.BoostType.PREMIUM,
        is_active=True
    ).order_by("duration_days")
    
    urgent_options = BoostOption.objects.filter(
        boost_type=BoostOption.BoostType.URGENT,
        is_active=True
    ).order_by("duration_days")
    
    prolongation_options = BoostOption.objects.filter(
        boost_type=BoostOption.BoostType.PROLONGATION,
        is_active=True
    ).order_by("duration_days")
    
    if request.method == "POST":
        boost_option_id = request.POST.get("boost_option")
        use_free_booster = request.POST.get("use_free_booster") == "on"
        
        if not boost_option_id:
            messages.error(request, "Veuillez sélectionner une option de boost")
        else:
            try:
                BoostService.apply_boost(
                    request.user,
                    ad_id,
                    int(boost_option_id),
                    use_free_booster=use_free_booster
                )
                
                boost_option = BoostOption.objects.get(id=boost_option_id)
                if use_free_booster:
                    messages.success(
                        request,
                        f"Boost {boost_option.name} appliqué avec succès (booster gratuit utilisé) !"
                    )
                else:
                    messages.success(
                        request,
                        f"Boost {boost_option.name} appliqué avec succès ! "
                        f"Montant débité : {boost_option.price} FCFA"
                    )
                return redirect("accounts:account_balance")
            except ValidationError as e:
                messages.error(request, str(e))
    
    return render(request, "accounts/boost_ad.html", {
        "ad": ad,
        "account": account,
        "premium_options": premium_options,
        "urgent_options": urgent_options,
        "prolongation_options": prolongation_options,
    })


@login_required
def cinetpay_notify(request: HttpRequest) -> HttpResponse:
    """Webhook CinetPay pour les notifications de paiement"""
    if request.method == "POST":
        data = request.POST.dict()
        signature = request.POST.get("signature", "")
        
        # Vérifier la signature
        if not CinetPayService.verify_webhook_signature(data, signature):
            return JsonResponse({"status": "error", "message": "Signature invalide"}, status=400)
        
        # Récupérer la transaction
        cinetpay_transaction_id = data.get("cpm_trans_id", "")
        transaction = Transaction.objects.filter(
            cinetpay_transaction_id=cinetpay_transaction_id
        ).first()
        
        if not transaction:
            return JsonResponse({"status": "error", "message": "Transaction introuvable"}, status=404)
        
        # Vérifier le statut du paiement
        payment_status = data.get("cpm_result", "")
        
        if payment_status == "00":  # Paiement réussi
            # Appliquer la recharge
            try:
                AccountService.apply_recharge(
                    transaction.user,
                    transaction.recharge_package.id,
                    cinetpay_transaction_id=cinetpay_transaction_id
                )
                transaction.status = Transaction.Status.COMPLETED
                transaction.save()
            except ValidationError:
                transaction.status = Transaction.Status.FAILED
                transaction.save()
        else:
            transaction.status = Transaction.Status.FAILED
            transaction.save()
        
        return JsonResponse({"status": "ok"})
    
    return JsonResponse({"status": "error"}, status=405)


@login_required
def cinetpay_return(request: HttpRequest) -> HttpResponse:
    """Page de retour après paiement CinetPay"""
    transaction_id = request.GET.get("transaction_id", "")
    
    if transaction_id:
        transaction = Transaction.objects.filter(
            cinetpay_transaction_id=transaction_id,
            user=request.user
        ).first()
        
        if transaction:
            if transaction.status == Transaction.Status.COMPLETED:
                messages.success(
                    request,
                    f"Paiement effectué avec succès ! Votre compte a été rechargé."
                )
            elif transaction.status == Transaction.Status.FAILED:
                messages.error(request, "Le paiement a échoué. Veuillez réessayer.")
            else:
                # Vérifier le statut
                payment_info = CinetPayService.verify_payment(transaction_id)
                if payment_info and payment_info.get("status") == "ACCEPTED":
                    try:
                        AccountService.apply_recharge(
                            transaction.user,
                            transaction.recharge_package.id,
                            cinetpay_transaction_id=transaction_id
                        )
                        transaction.status = Transaction.Status.COMPLETED
                        transaction.save()
                        messages.success(
                            request,
                            f"Paiement effectué avec succès ! Votre compte a été rechargé."
                        )
                    except ValidationError as e:
                        messages.error(request, str(e))
                else:
                    messages.warning(request, "Paiement en attente de confirmation.")
    
    return redirect("accounts:account_balance")
