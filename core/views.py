import json
import logging
from django.shortcuts import render, redirect
from django.http import HttpRequest, HttpResponse, JsonResponse
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.utils import timezone
from django.db.models import Q
from django.core.exceptions import ValidationError
from django.conf import settings
from django.views.static import serve
from django.contrib.auth import get_user_model
from ads.models import Ad, AdMedia
from ads.forms import AdForm
from accounts.models import Profile
from accounts.tasks import send_ad_published_email

logger = logging.getLogger(__name__)
User = get_user_model()


def _phone_used_by_other_account(phone: str, current_user) -> bool:
    """True si ce numéro est déjà utilisé par un autre compte (user ou profil)."""
    phone = (phone or "").strip()
    if not phone:
        return False
    if User.objects.filter(phone_e164=phone).exclude(pk=current_user.pk).exists():
        return True
    if Profile.objects.filter(Q(phone2_e164=phone) | Q(whatsapp_e164=phone)).exclude(user=current_user).exists():
        return True
    return False


def landing(request: HttpRequest) -> HttpResponse:
    """Page d'accueil - redirige vers /ads"""
    from ads.views import ad_list

    return ad_list(request)


def age_gate(request: HttpRequest) -> HttpResponse:
    if request.method == "POST":
        response = redirect("/")
        response.set_cookie(
            "age_gate_accepted",
            "1",
            max_age=60 * 60 * 24 * 365,
            secure=not settings.DEBUG,  # HTTPS uniquement en production
            httponly=False,             # Le JS doit pouvoir lire ce cookie
            samesite="Lax",
        )
        return response
    return render(request, "core/age_gate.html")


def favicon(request: HttpRequest) -> HttpResponse:
    """Servir le favicon — 204 No Content si le fichier n'existe pas (browsers l'acceptent)."""
    import os
    favicon_path = os.path.join(settings.STATICFILES_DIRS[0], "favicon.png")
    if os.path.exists(favicon_path):
        return serve(request, "favicon.png", document_root=settings.STATICFILES_DIRS[0])
    return HttpResponse(status=204)


def health_check(request: HttpRequest) -> JsonResponse:
    """Endpoint de santé pour Vercel, Docker et les outils de monitoring."""
    from django.db import connection
    try:
        connection.ensure_connection()
        db_ok = True
    except Exception:
        db_ok = False
    status = 200 if db_ok else 503
    return JsonResponse({"status": "ok" if db_ok else "degraded", "db": db_ok}, status=status)


@login_required
def post(request: HttpRequest) -> HttpResponse:
    """Formulaire pour publier une annonce"""
    if request.method == "POST":
        form = AdForm(request.POST, request.FILES)
        if form.is_valid():
            phone1 = (form.cleaned_data.get("phone1") or "").strip()
            phone2 = (form.cleaned_data.get("phone2") or "").strip()

            # Validation des photos : au moins 1 obligatoire, max 5, taille et MIME
            uploaded_images = request.FILES.getlist("images")
            image_error = None
            if not uploaded_images:
                image_error = "Au moins une photo est obligatoire pour publier une annonce."
            elif len(uploaded_images) > 5:
                image_error = "Vous ne pouvez pas envoyer plus de 5 photos."
            else:
                for img in uploaded_images:
                    if img.size > 5 * 1024 * 1024:
                        image_error = f"Photo « {img.name} » trop volumineuse (max 5 Mo)."
                        break
                    if not img.content_type.startswith("image/"):
                        image_error = f"Fichier « {img.name} » n'est pas une image valide."
                        break
            if image_error:
                return render(request, "core/post.html", {
                    "form": form,
                    "subcategory_choices_json": json.dumps(list(Ad.SUBCATEGORY_CHOICES)),
                    "image_error": image_error,
                })

            if _phone_used_by_other_account(phone1, request.user):
                form.add_error("phone1", "Ce numéro est déjà utilisé par un autre compte.")
                return render(request, "core/post.html", {"form": form, "subcategory_choices_json": json.dumps(list(Ad.SUBCATEGORY_CHOICES))})
            if phone2 and _phone_used_by_other_account(phone2, request.user):
                form.add_error("phone2", "Ce numéro est déjà utilisé par un autre compte.")
                return render(request, "core/post.html", {"form": form, "subcategory_choices_json": json.dumps(list(Ad.SUBCATEGORY_CHOICES))})

            profile, created = Profile.objects.get_or_create(
                user=request.user,
                defaults={
                    "display_name": request.user.username,
                    "whatsapp_e164": phone2 or phone1,
                    "contact_prefs": form.cleaned_data["contact_methods"],
                },
            )
            if not created:
                profile.whatsapp_e164 = phone2 or phone1
                profile.phone2_e164 = phone2 or None
                profile.contact_prefs = form.cleaned_data["contact_methods"]
                profile.save()

            request.user.phone_e164 = phone1
            request.user.save()

            # Déterminer le statut selon si le profil est validé
            is_verified = profile.is_verified

            # Collecter les données supplémentaires selon la catégorie
            additional_data = {}
            category = form.cleaned_data["category"]
            
            if category == "villas_residences":
                if form.cleaned_data.get("prix_jours_ouvrables"):
                    additional_data["prix_jours_ouvrables"] = float(form.cleaned_data["prix_jours_ouvrables"])
                if form.cleaned_data.get("prix_jours_non_ouvrables"):
                    additional_data["prix_jours_non_ouvrables"] = float(form.cleaned_data["prix_jours_non_ouvrables"])
                if form.cleaned_data.get("surface"):
                    additional_data["surface"] = int(form.cleaned_data["surface"])
                if form.cleaned_data.get("nombre_chambres"):
                    additional_data["nombre_chambres"] = int(form.cleaned_data["nombre_chambres"])
            
            elif category == "maisons_appartements":
                if form.cleaned_data.get("prix_vente"):
                    additional_data["prix_vente"] = float(form.cleaned_data["prix_vente"])
                if form.cleaned_data.get("surface"):
                    additional_data["surface"] = int(form.cleaned_data["surface"])
                if form.cleaned_data.get("nombre_chambres"):
                    additional_data["nombre_chambres"] = int(form.cleaned_data["nombre_chambres"])
                if form.cleaned_data.get("nombre_salles_bain"):
                    additional_data["nombre_salles_bain"] = int(form.cleaned_data["nombre_salles_bain"])
            
            elif category == "terrains":
                if form.cleaned_data.get("prix"):
                    additional_data["prix"] = float(form.cleaned_data["prix"])
                if form.cleaned_data.get("surface"):
                    additional_data["surface"] = int(form.cleaned_data["surface"])
            
            elif category == "locations":
                if form.cleaned_data.get("loyer_mensuel"):
                    additional_data["loyer_mensuel"] = float(form.cleaned_data["loyer_mensuel"])
                if form.cleaned_data.get("charges"):
                    additional_data["charges"] = float(form.cleaned_data["charges"])
                if form.cleaned_data.get("caution"):
                    additional_data["caution"] = float(form.cleaned_data["caution"])
                if form.cleaned_data.get("surface"):
                    additional_data["surface"] = int(form.cleaned_data["surface"])
                if form.cleaned_data.get("nombre_chambres"):
                    additional_data["nombre_chambres"] = int(form.cleaned_data["nombre_chambres"])

            # Créer l'annonce en DRAFT (en attente de paiement)
            ad = Ad.objects.create(
                user=request.user,
                title=form.cleaned_data["title"],
                description_sanitized=form.cleaned_data["description"],
                category=form.cleaned_data["category"],
                subcategories=form.cleaned_data["subcategories"],
                city=form.cleaned_data["city"],
                additional_data=additional_data,
                status=Ad.Status.DRAFT,
                # expires_at sera fixé après paiement (5 ou 7 jours)
                expires_at=timezone.now() + timezone.timedelta(days=5),
            )

            # Enregistrer les images (déjà validées avant la création de l'annonce)
            images_added = 0
            for image in uploaded_images:
                try:
                    AdMedia.objects.create(ad=ad, image=image, is_primary=(images_added == 0))
                    images_added += 1
                except Exception as e:
                    logger.exception("Erreur enregistrement photo annonce %s (photo ignorée): %s", ad.id, e)

            # En liste, l'annonce n'apparaît qu'une fois toutes les images traitées (filigrane + miniature)
            if images_added and getattr(settings, "USE_ASYNC_IMAGE_PROCESSING", False):
                ad.image_processing_done = False
                ad.save(update_fields=["image_processing_done"])

            # Rediriger vers le formulaire de paiement (PawaPay)
            request.session["pending_ad_id"] = ad.id
            return redirect("payments:pay_form")
    else:
        initial_data = {}
        try:
            if hasattr(request.user, "profile") and request.user.profile:
                initial_data = {
                    "phone1": request.user.phone_e164 or "",
                    "phone2": getattr(request.user.profile, "phone2_e164", None) or request.user.profile.whatsapp_e164 or "",
                    "contact_methods": request.user.profile.contact_prefs or [],
                }
            else:
                initial_data = {
                    "phone1": request.user.phone_e164 or "",
                    "phone2": "",
                    "contact_methods": [],
                }
        except Exception:
            initial_data = {"phone1": "", "phone2": "", "contact_methods": []}
        form = AdForm(initial=initial_data)

    return render(request, "core/post.html", {"form": form, "subcategory_choices_json": json.dumps(list(Ad.SUBCATEGORY_CHOICES))})


@login_required
def edit_ad(request: HttpRequest, ad_id: int) -> HttpResponse:
    """Modifier une annonce existante"""
    try:
        ad = Ad.objects.get(id=ad_id, user=request.user)
    except Ad.DoesNotExist:
        messages.error(request, "Annonce non trouvée.")
        return redirect("/dashboard/")

    if request.method == "POST":
        form = AdForm(request.POST, request.FILES)
        if form.is_valid():
            phone1 = (form.cleaned_data.get("phone1") or "").strip()
            phone2 = (form.cleaned_data.get("phone2") or "").strip()
            if _phone_used_by_other_account(phone1, request.user):
                form.add_error("phone1", "Ce numéro est déjà utilisé par un autre compte.")
                return render(request, "core/edit_ad.html", {"form": form, "ad": ad})
            if phone2 and _phone_used_by_other_account(phone2, request.user):
                form.add_error("phone2", "Ce numéro est déjà utilisé par un autre compte.")
                return render(request, "core/edit_ad.html", {"form": form, "ad": ad})

            ad.title = form.cleaned_data["title"]
            ad.description_sanitized = form.cleaned_data["description"]
            ad.category = form.cleaned_data["category"]
            ad.subcategories = form.cleaned_data["subcategories"]
            ad.city = form.cleaned_data["city"]
            ad.save()

            profile, created = Profile.objects.get_or_create(
                user=request.user,
                defaults={
                    "display_name": request.user.username,
                    "whatsapp_e164": phone2 or phone1,
                    "phone2_e164": phone2 or None,
                    "contact_prefs": form.cleaned_data["contact_methods"],
                },
            )
            if not created:
                profile.whatsapp_e164 = phone2 or phone1
                profile.phone2_e164 = phone2 or None
                profile.contact_prefs = form.cleaned_data["contact_methods"]
                profile.save()

            request.user.phone_e164 = phone1
            request.user.save()

            # Gérer les nouvelles images - remplacer toutes les images existantes
            new_images = request.FILES.getlist("images")
            if new_images:
                # Validation : max 5, taille, MIME
                image_error = None
                if len(new_images) > 5:
                    image_error = "Vous ne pouvez pas envoyer plus de 5 photos."
                else:
                    for img in new_images:
                        if img.size > 5 * 1024 * 1024:
                            image_error = f"Photo « {img.name} » trop volumineuse (max 5 Mo)."
                            break
                        if not img.content_type.startswith("image/"):
                            image_error = f"Fichier « {img.name} » n'est pas une image valide."
                            break
                if image_error:
                    return render(request, "core/edit_ad.html", {"form": form, "ad": ad, "image_error": image_error})

                # Supprimer toutes les images existantes
                existing_media = AdMedia.objects.filter(ad=ad)
                for media in existing_media:
                    if media.image:
                        media.image.delete(save=False)
                    media.delete()

                # Enregistrer les nouvelles images
                images_added = 0
                for image in new_images:
                    try:
                        AdMedia.objects.create(ad=ad, image=image, is_primary=(images_added == 0))
                        images_added += 1
                    except Exception as e:
                        logger.exception(
                            "Erreur enregistrement photo annonce %s (photo ignorée): %s", ad.id, e
                        )

                if images_added and getattr(settings, "USE_ASYNC_IMAGE_PROCESSING", False):
                    ad.image_processing_done = False
                    ad.save(update_fields=["image_processing_done"])

            messages.success(request, "Annonce modifiée avec succès !")
            return redirect("/dashboard/")
    else:
        form = AdForm(
            initial={
                "title": ad.title,
                "category": ad.category,
                "subcategories": ad.subcategories,
                "description": ad.description_sanitized,
                "city": ad.city,
                "phone1": request.user.phone_e164 or "",
                "phone2": (
                    getattr(request.user.profile, "phone2_e164", None) or request.user.profile.whatsapp_e164
                    if hasattr(request.user, "profile") and request.user.profile
                    else ""
                ),
                "contact_methods": (
                    request.user.profile.contact_prefs if hasattr(request.user, "profile") else []
                ),
            }
        )

    return render(request, "core/edit_ad.html", {"form": form, "ad": ad})


def dashboard(request: HttpRequest) -> HttpResponse:
    if not request.user.is_authenticated:
        return redirect("/auth/login/")
    
    # S'assurer que le profil existe
    try:
        profile = request.user.profile
    except Profile.DoesNotExist:
        profile = Profile.objects.create(
            user=request.user,
            display_name=request.user.username
        )
    
    # Afficher toutes les annonces de l'utilisateur (préchargement city + médias pour éviter 500)
    my_ads = (
        Ad.objects.filter(user=request.user)
        .select_related("city")
        .order_by("-created_at")
        .prefetch_related("media")
    )
    return render(request, "core/dashboard.html", {"ads": my_ads, "profile": profile})


# Pages légales


def legal_tos(request: HttpRequest) -> HttpResponse:
    return render(request, "legal/tos.html")


def legal_privacy(request: HttpRequest) -> HttpResponse:
    return render(request, "legal/privacy.html")


def legal_content_policy(request: HttpRequest) -> HttpResponse:
    return render(request, "legal/content_policy.html")


# Report d'annonce


def report_ad(request: HttpRequest, ad_id: int) -> HttpResponse:
    ad = Ad.objects.filter(id=ad_id, status=Ad.Status.APPROVED).first()
    if not ad:
        return render(request, "core/404.html", status=404)
    if request.method == "POST":
        # Squelette: on affiche un merci (la persistance est gérée ailleurs)
        return render(request, "core/report.html", {"ad": ad, "submitted": True})
    return render(request, "core/report.html", {"ad": ad, "submitted": False})


def csrf_failure(request: HttpRequest, reason: str = "") -> HttpResponse:
    """Vue personnalisée pour l'erreur 403 CSRF : message clair et lien pour réessayer."""
    return render(request, "core/403_csrf.html", status=403)


def page_not_found_view(request: HttpRequest, exception: Exception) -> HttpResponse:
    """Handler 404 global : page avec noindex pour que Google ne tente pas d'indexer les URLs mortes."""
    return render(request, "core/404.html", status=404)


def server_error_view(request: HttpRequest) -> HttpResponse:
    """Handler 500 global : page d'erreur propre pour limiter l'impact sur l'indexation."""
    return render(request, "core/500.html", status=500)
