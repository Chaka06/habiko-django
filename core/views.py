from django.shortcuts import render, redirect
from django.http import HttpRequest, HttpResponse
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.utils import timezone
from django.db.models import Q
from django.core.exceptions import ValidationError
from ads.models import Ad, AdMedia
from ads.forms import AdForm
from accounts.models import Profile
from accounts.tasks import send_ad_published_email


def landing(request: HttpRequest) -> HttpResponse:
    """Page d'accueil - redirige vers /ads"""
    from ads.views import ad_list

    return ad_list(request)


def age_gate(request: HttpRequest) -> HttpResponse:
    if request.method == "POST":
        response = redirect("/")
        response.set_cookie("age_gate_accepted", "1", max_age=60 * 60 * 24 * 365)
        return response
    return render(request, "core/age_gate.html")


@login_required
def post(request: HttpRequest) -> HttpResponse:
    """Formulaire pour publier une annonce"""
    if request.method == "POST":
        form = AdForm(request.POST, request.FILES)
        if form.is_valid():
            # Créer/mettre à jour le profil utilisateur
            profile, created = Profile.objects.get_or_create(
                user=request.user,
                defaults={
                    "display_name": request.user.username,
                    "whatsapp_e164": form.cleaned_data["phone2"] or form.cleaned_data["phone1"],
                    "contact_prefs": form.cleaned_data["contact_methods"],
                },
            )
            if not created:
                profile.whatsapp_e164 = form.cleaned_data["phone2"] or form.cleaned_data["phone1"]
                profile.contact_prefs = form.cleaned_data["contact_methods"]
                profile.save()

            # Mettre à jour le numéro de téléphone dans l'utilisateur
            request.user.phone_e164 = form.cleaned_data["phone1"]
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

            # Créer l'annonce
            ad = Ad.objects.create(
                user=request.user,
                title=form.cleaned_data["title"],
                description_sanitized=form.cleaned_data["description"],
                category=form.cleaned_data["category"],
                subcategories=form.cleaned_data["subcategories"],
                city=form.cleaned_data["city"],
                additional_data=additional_data,
                status=Ad.Status.APPROVED if is_verified else Ad.Status.PENDING,
                expires_at=timezone.now() + timezone.timedelta(days=14),
            )

            # Si l'annonce est en attente, programmer l'approbation automatique après 10 secondes
            if not is_verified:
                from ads.tasks import auto_approve_ad

                auto_approve_ad.apply_async(args=[ad.id], countdown=10)
                print(f"Annonce {ad.id} créée en attente (approbation automatique programmée)")
            else:
                # Si l'utilisateur est vérifié, envoyer l'email de confirmation immédiatement
                send_ad_published_email.delay(ad.id)
                print(f"Annonce {ad.id} créée et approuvée (email envoyé)")

            # Ajouter les images avec validation
            image_fields = ["image1", "image2", "image3", "image4", "image5"]
            images_added = 0

            for i, field_name in enumerate(image_fields):
                if field_name in request.FILES and request.FILES[field_name]:
                    image = request.FILES[field_name]

                    # Validation de la taille
                    if image.size > 5 * 1024 * 1024:  # 5MB max
                        messages.error(request, f"Photo {image.name} trop volumineuse (max 5MB).")
                        return render(request, "core/post.html", {"form": form})

                    # Validation du type MIME
                    if not image.content_type.startswith("image/"):
                        messages.error(request, f"Fichier {image.name} n'est pas une image.")
                        return render(request, "core/post.html", {"form": form})

                    AdMedia.objects.create(ad=ad, image=image, is_primary=(images_added == 0))
                    images_added += 1

            # Envoyer l'email de confirmation (désactivé temporairement pour éviter les erreurs Redis)
            # send_ad_published_email.delay(ad.id)

            if is_verified:
                messages.success(
                    request, "Annonce créée avec succès ! Elle est maintenant visible."
                )
            else:
                messages.success(
                    request,
                    "Annonce créée avec succès ! Elle sera visible après validation de votre profil par email.",
                )
            return redirect("/dashboard/")
    else:
        # Initialiser le formulaire avec les données de l'utilisateur si disponibles
        initial_data = {}
        try:
            if hasattr(request.user, 'profile') and request.user.profile:
                initial_data = {
                    "phone1": request.user.phone_e164 or "",
                    "phone2": request.user.profile.whatsapp_e164 or "",
                    "contact_methods": request.user.profile.contact_prefs or [],
                }
            elif request.user.is_authenticated:
                initial_data = {
                    "phone1": request.user.phone_e164 or "",
                    "phone2": "",
                    "contact_methods": [],
                }
        except Exception:
            # Si erreur, utiliser des valeurs par défaut
            initial_data = {
                "phone1": "",
                "phone2": "",
                "contact_methods": [],
            }
        
        form = AdForm(initial=initial_data)

    return render(request, "core/post.html", {"form": form})


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
            # Mettre à jour l'annonce
            ad.title = form.cleaned_data["title"]
            ad.description_sanitized = form.cleaned_data["description"]
            ad.category = form.cleaned_data["category"]
            ad.subcategories = form.cleaned_data["subcategories"]
            ad.city = form.cleaned_data["city"]
            ad.save()

            # Mettre à jour le profil utilisateur
            profile, created = Profile.objects.get_or_create(
                user=request.user,
                defaults={
                    "display_name": request.user.username,
                    "whatsapp_e164": form.cleaned_data["phone2"] or form.cleaned_data["phone1"],
                    "contact_prefs": form.cleaned_data["contact_methods"],
                },
            )
            if not created:
                profile.whatsapp_e164 = form.cleaned_data["phone2"] or form.cleaned_data["phone1"]
                profile.contact_prefs = form.cleaned_data["contact_methods"]
                profile.save()

            # Mettre à jour le numéro de téléphone dans l'utilisateur
            request.user.phone_e164 = form.cleaned_data["phone1"]
            request.user.save()

            # Gérer les nouvelles images - remplacer toutes les images existantes
            if any(
                field_name in request.FILES and request.FILES[field_name]
                for field_name in ["image1", "image2", "image3", "image4", "image5"]
            ):
                # Supprimer toutes les images existantes
                existing_media = AdMedia.objects.filter(ad=ad)
                for media in existing_media:
                    if media.image:
                        media.image.delete(save=False)
                    media.delete()

                # Ajouter les nouvelles images
                image_fields = ["image1", "image2", "image3", "image4", "image5"]
                images_added = 0

                for i, field_name in enumerate(image_fields):
                    if field_name in request.FILES and request.FILES[field_name]:
                        image = request.FILES[field_name]

                        # Validation de la taille
                        if image.size > 5 * 1024 * 1024:  # 5MB max
                            messages.error(
                                request, f"Photo {image.name} trop volumineuse (max 5MB)."
                            )
                            return render(request, "core/edit_ad.html", {"form": form, "ad": ad})

                        # Validation du type MIME
                        if not image.content_type.startswith("image/"):
                            messages.error(request, f"Fichier {image.name} n'est pas une image.")
                            return render(request, "core/edit_ad.html", {"form": form, "ad": ad})

                        AdMedia.objects.create(ad=ad, image=image, is_primary=(images_added == 0))
                        images_added += 1

            messages.success(request, "Annonce modifiée avec succès !")
            return redirect("/dashboard/")
    else:
        # Pré-remplir le formulaire avec les données existantes
        form = AdForm(
            initial={
                "title": ad.title,
                "category": ad.category,
                "subcategories": ad.subcategories,
                "description": ad.description_sanitized,
                "city": ad.city,
                "phone1": request.user.phone_e164,
                "phone2": (
                    request.user.profile.whatsapp_e164 if hasattr(request.user, "profile") else ""
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
    
    # Afficher toutes les annonces de l'utilisateur, avec préchargement des médias
    my_ads = (
        Ad.objects.filter(user=request.user)
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


# Create your views here.
