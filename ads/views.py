import time as _time

from django.shortcuts import render, get_object_or_404
from django.http import HttpRequest, HttpResponse, JsonResponse
from django.contrib.auth.decorators import login_required
from django.conf import settings
from django.db.models import Q, F, Case, When, Value, IntegerField
from django.core.cache import cache
from django.db import connection
from django.core.paginator import Paginator
from django.views.decorators.http import require_POST, require_GET
from django.views.decorators.cache import cache_page
from django.views.decorators.csrf import csrf_exempt
from .models import Ad, AdMedia, City, Favorite
from core.context_processors import get_ad_list_version


@require_GET
def ad_list(request: HttpRequest) -> HttpResponse:
    city = request.GET.get("city", "").strip()
    # Rejeter les catégories invalides pour éviter des requêtes inutiles
    _raw_category = request.GET.get("category", "").strip()
    _valid_categories = {v for v, _ in Ad.Category.choices}
    category = _raw_category if _raw_category in _valid_categories else ""
    # N'accepter le filtre provider que par username (évite l'énumération par user_id)
    _raw_provider = request.GET.get("provider", "").strip()
    provider = _raw_provider if _raw_provider and not _raw_provider.isdigit() else ""
    # Borner le numéro de page pour éviter le chargement de toute la liste en RAM
    try:
        page = max(1, min(int(request.GET.get("page", "1")), 500))
    except (ValueError, TypeError):
        page = 1
    q = request.GET.get("q", "").strip()
    boost = request.GET.get("boost", "").strip()  # urgent | premium | boosted

    # Bucket de 5 minutes : la rotation des annonces boostées change toutes les 5 min.
    time_bucket = int(_time.time() / 300)

    # Cache uniquement pour les utilisateurs anonymes (évite de servir la nav
    # "Se connecter" aux utilisateurs connectés). La clé inclut time_bucket pour
    # que la rotation 2 min invalide automatiquement le cache.
    cache_key = None
    if not q and not request.user.is_authenticated:
        version = get_ad_list_version()
        cache_key = f"ad_list:v{version}:{city}:{category}:{provider}:{boost}:{page}:{time_bucket}"
        cached = cache.get(cache_key)
        if cached is not None:
            return cached

    common_qs = (
        Ad.objects
        .select_related("city", "user", "user__profile")
        .prefetch_related("media")
    )

    def apply_filters(qs):
        if city:
            qs = qs.filter(city__slug=city)
        if category:
            qs = qs.filter(category=category)
        if provider:
            # Uniquement par username — l'ID est refusé en amont (prévient l'énumération)
            qs = qs.filter(user__username=provider)
        if q:
            q_search = Q(title__icontains=q) | Q(description_sanitized__icontains=q)
            # JSON array contains — supported on PostgreSQL, not SQLite
            _supports_json_contains = connection.vendor == "postgresql"
            for sub in Ad.SUBCATEGORY_CHOICES:
                if q.lower() in sub.lower():
                    if _supports_json_contains:
                        q_search |= Q(subcategories__contains=[sub])
                    else:
                        q_search |= Q(subcategories__icontains=sub)
            qs = qs.filter(q_search)
        return qs

    # Annonces actives : boosted séparées des normales pour mélange aléatoire
    base_approved = common_qs.filter(status=Ad.Status.APPROVED, image_processing_done=True)
    if boost == "urgent":
        base_approved = base_approved.filter(is_urgent=True)
    elif boost == "premium":
        base_approved = base_approved.filter(is_premium=True)
    elif boost == "boosted":
        base_approved = base_approved.filter(is_boosted=True)
    active_qs = apply_filters(base_approved.order_by("-created_at"))
    active_ads = list(active_qs)

    boosted_ads = [a for a in active_ads if a.is_premium or a.is_boosted or a.is_urgent]
    regular_ads = [a for a in active_ads if not (a.is_premium or a.is_boosted or a.is_urgent)]

    # Rotation round-robin des boostées toutes les 5 minutes :
    # chaque annonce boostée passe à son tour en tête de liste.
    # L'offset change avec time_bucket (= int(now/300)), ce qui invalide aussi le cache.
    if boosted_ads:
        n = len(boosted_ads)
        offset = time_bucket % n
        boosted_ads = boosted_ads[offset:] + boosted_ads[:offset]

    # Boostées toujours en haut, annonces normales en bas
    final_list = boosted_ads + regular_ads

    # Annonces expirées toujours en bas
    expired_ads = list(apply_filters(
        common_qs.filter(status=Ad.Status.EXPIRED, image_processing_done=True)
        .order_by("-created_at")
    ))
    final_list.extend(expired_ads)

    selected_city = None
    selected_category = None
    if city:
        try:
            selected_city = City.objects.get(slug=city)
        except City.DoesNotExist:
            pass
    if category:
        selected_category = category

    paginator = Paginator(final_list, 10)
    page_obj = paginator.get_page(page)

    cities = cache.get("all_cities")
    if cities is None:
        cities = list(City.objects.all())
        cache.set("all_cities", cities, 86400)  # 24h

    _visible_statuses = [Ad.Status.APPROVED, Ad.Status.EXPIRED]

    total_approved_ads = cache.get("total_approved_ads_count")
    if total_approved_ads is None:
        total_approved_ads = Ad.objects.filter(status__in=_visible_statuses).count()
        cache.set("total_approved_ads_count", total_approved_ads, 300)

    city_counts = cache.get("city_ad_counts")
    if city_counts is None:
        from django.db.models import Count as _Count
        city_counts = list(
            City.objects
            .annotate(ad_count=_Count(
                "ad",
                filter=Q(ad__status__in=_visible_statuses)
            ))
            .filter(ad_count__gt=0)
            .order_by("-ad_count")[:12]
        )
        cache.set("city_ad_counts", city_counts, 300)

    category_counts = cache.get("category_ad_counts")
    if category_counts is None:
        from django.db.models import Count as _Count
        category_counts = dict(
            Ad.objects.filter(status__in=_visible_statuses)
            .values("category")
            .annotate(n=_Count("id"))
            .values_list("category", "n")
        )
        cache.set("category_ad_counts", category_counts, 300)

    response = render(
        request,
        "ads/list.html",
        {
            "ads": page_obj,
            "cities": cities,
            "page_obj": page_obj,
            "is_paginated": page_obj.has_other_pages(),
            "selected_city": selected_city,
            "selected_category": selected_category,
            "category_choices": Ad.Category.choices,
            "seo_city_text": getattr(request, "_seo_city_text", ""),
            "total_approved_ads": total_approved_ads,
            "city_counts": city_counts,
            "category_counts": category_counts,
        },
    )

    if cache_key is not None:
        # TTL aligné sur le bucket de 2 min (120s) pour que le cache ne survive pas
        # à la prochaine rotation de positions.
        cache.set(cache_key, response, 120)

    return response


# Textes SEO longs par ville, inspirés de jedolo.com (contenu unique, localisé)
_CITY_SEO_TEXTS = {
    "abidjan": (
        "Abidjan, capitale économique de la Côte d'Ivoire, concentre la majorité des "
        "annonces bizi et escort. Que vous soyez à Cocody, Plateau, Yopougon, Marcory, "
        "Treichville ou Koumassi, KIABA vous connecte directement avec des escort girls, "
        "escort boys et transgenres disponibles 24h/24. Massage sexuel, finition, sodomie, "
        "partouze — toutes les annonces sont vérifiées et publiées par leurs auteures."
    ),
    "bouake": (
        "Bouaké, deuxième ville de Côte d'Ivoire, dispose d'un marché bizi actif. "
        "Retrouvez sur KIABA les meilleures annonces escort girl et escort boy de Bouaké : "
        "massage sexuel, rencontres adultes et services complets. Annonces vérifiées, "
        "contact direct par WhatsApp ou appel."
    ),
    "daloa": (
        "Daloa, capitale du Haut-Sassandra, accueille de nombreuses escort girls et bizi. "
        "KIABA centralise toutes les annonces adultes de Daloa : escortes féminines, "
        "escort boys, transgenres. Massage sexuel, finition, services complets disponibles."
    ),
    "yamoussoukro": (
        "Yamoussoukro, capitale politique de la Côte d'Ivoire, dispose d'annonces escort "
        "et bizi publiées sur KIABA. Escort girls, escort boys et transgenres disponibles "
        "pour massage sexuel et rencontres adultes dans la ville."
    ),
    "korhogo": (
        "Korhogo, chef-lieu du Nord ivoirien, est présente sur KIABA avec des annonces "
        "bizi et escort girl. Services adultes : massage sexuel, finition, rencontres. "
        "Contactez directement via WhatsApp ou appel."
    ),
}


@require_GET
def ad_list_seo(request: HttpRequest, city_slug: str = "", category: str = "") -> HttpResponse:
    """Handler pour URLs SEO propres : /ads/escort-girl-abidjan/, /ads/bizi-abidjan/, etc."""
    # Injecter city_slug et category dans GET sans modifier l'objet original
    get = request.GET.copy()
    if city_slug:
        get.setdefault("city", city_slug)
    if category:
        get.setdefault("category", category)
    request.GET = get
    # Passer le texte SEO localisé si disponible
    seo_text = _CITY_SEO_TEXTS.get(city_slug, "") if city_slug else ""
    # On appelle ad_list mais on injecte seo_text via un attribut de requête
    request._seo_city_text = seo_text
    return ad_list(request)


def search_suggestions(request: HttpRequest) -> JsonResponse:
    """Retourne des suggestions de recherche (catégories, sous-catégories, termes des annonces)."""
    q = (request.GET.get("q") or "").strip()[:80]
    if len(q) < 2:
        return JsonResponse({"suggestions": []})

    cache_key = f"search_suggestions_{q.lower()}"
    cached = cache.get(cache_key)
    if cached is not None:
        return JsonResponse({"suggestions": cached})

    q_lower = q.lower()
    suggestions = []

    # Catégories dont le label contient la requête
    for value, label in Ad.Category.choices:
        if q_lower in label.lower():
            suggestions.append({"type": "category", "label": label, "value": value})

    # Sous-catégories qui contiennent la requête
    for sub in Ad.SUBCATEGORY_CHOICES:
        if q_lower in sub.lower() and sub not in [s.get("label") for s in suggestions]:
            suggestions.append({"type": "subcategory", "label": sub, "value": sub})

    # Titres d'annonces qui contiennent la requête (max 8)
    title_matches = (
        Ad.objects.filter(status=Ad.Status.APPROVED, title__icontains=q)
        .values_list("title", flat=True)
        .distinct()[:8]
    )
    for title in title_matches:
        if title and title not in [s.get("label") for s in suggestions]:
            suggestions.append({"type": "title", "label": title[:60] + ("…" if len(title) > 60 else ""), "value": title})

    result = suggestions[:15]
    cache.set(cache_key, result, 300)  # 5 min
    return JsonResponse({"suggestions": result})


def ad_detail(request: HttpRequest, slug: str) -> HttpResponse:
    # Cache uniquement pour les utilisateurs anonymes.
    # Le HTML rendu contient la nav (user.is_authenticated) : mettre en cache pour tous
    # ferait apparaître "Se connecter" aux utilisateurs connectés.
    if not request.user.is_authenticated:
        cache_key = f"ad_detail:{slug}"
        cached = cache.get(cache_key)
        if cached is not None:
            return cached

    # Annonce archivée/expirée → 410 Gone (signal fort pour Google : désindexer cette URL)
    if Ad.objects.filter(slug=slug, status=Ad.Status.ARCHIVED).exists():
        from django.template.loader import render_to_string
        return HttpResponse(
            render_to_string("core/404.html", {"reason": "expired"}, request=request),
            status=410,
            content_type="text/html",
        )

    ad = get_object_or_404(
        Ad.objects.filter(status__in=[Ad.Status.APPROVED, Ad.Status.EXPIRED], image_processing_done=True)
        .select_related("city", "user", "user__profile")
        .prefetch_related("media"),
        slug=slug,
    )

    # Annonces similaires : une seule requête (même catégorie, priorité même ville)
    similar_ads = (
        Ad.objects.filter(status__in=[Ad.Status.APPROVED, Ad.Status.EXPIRED], image_processing_done=True, category=ad.category)
        .exclude(id=ad.id)
        .select_related("city", "user", "user__profile")
        .prefetch_related("media")
        .annotate(same_city=Case(When(city_id=ad.city_id, then=Value(1)), default=Value(0), output_field=IntegerField()))
        .order_by("-same_city", "-created_at")[:5]
    )

    is_favorited = (
        request.user.is_authenticated
        and Favorite.objects.filter(user=request.user, ad=ad).exists()
    )

    response = render(request, "ads/detail.html", {"ad": ad, "similar_ads": similar_ads, "is_favorited": is_favorited})

    if not request.user.is_authenticated:
        cache.set(f"ad_detail:{slug}", response, 120)  # 2 min, anonymes seulement

    return response


@csrf_exempt
@require_POST
def record_ad_view(request: HttpRequest, slug: str) -> JsonResponse:
    """
    Enregistre une vue pour l'annonce (appelé côté client après 5 secondes sur la page détail).
    Une seule vue par annonce et par session pour éviter les doublons (rafraîchissement, etc.).
    """
    ad = get_object_or_404(
        Ad.objects.filter(status=Ad.Status.APPROVED),
        slug=slug,
    )
    # Ne pas compter si le visiteur est l'auteur de l'annonce (évite d'inflater ses propres stats)
    if request.user.is_authenticated and ad.user_id == request.user.id:
        return JsonResponse({"ok": True, "recorded": False, "reason": "owner"})

    session_views = request.session.get("ad_views_recorded") or []
    if ad.id in session_views:
        return JsonResponse({"ok": True, "recorded": False})

    Ad.objects.filter(pk=ad.id).update(views_count=F("views_count") + 1)
    session_views = list(session_views) + [ad.id]
    request.session["ad_views_recorded"] = session_views
    return JsonResponse({"ok": True, "recorded": True})


@login_required
@require_POST
def toggle_favorite(request: HttpRequest, ad_id: int) -> JsonResponse:
    """Ajoute ou retire une annonce des favoris de l'utilisateur (toggle)."""
    ad = get_object_or_404(Ad, pk=ad_id, status__in=[Ad.Status.APPROVED, Ad.Status.EXPIRED])
    fav, created = Favorite.objects.get_or_create(user=request.user, ad=ad)
    if not created:
        fav.delete()
    return JsonResponse({"favorited": created, "ad_id": ad_id})


@login_required
def favorites_list(request: HttpRequest) -> HttpResponse:
    """Page listant les annonces mises en favoris par l'utilisateur connecté."""
    favs = (
        Favorite.objects.filter(user=request.user)
        .select_related("ad", "ad__city", "ad__user", "ad__user__profile")
        .prefetch_related("ad__media")
    )
    return render(request, "ads/favorites.html", {"favorites": favs})


@csrf_exempt
def cron_apply_watermarks(request: HttpRequest) -> JsonResponse:
    """
    Endpoint appelé par Vercel Cron toutes les heures pour appliquer le filigrane
    aux images qui n'en ont pas encore (traitement par lots de 10).

    Sécurité : accepte uniquement les requêtes Vercel Cron (X-Vercel-Cron: 1)
    ou les requêtes avec le bon CRON_SECRET en header.
    """
    is_vercel_cron = request.META.get("HTTP_X_VERCEL_CRON") == "1"
    secret = getattr(settings, "CRON_SECRET", "")
    has_secret = secret and request.META.get("HTTP_X_CRON_SECRET") == secret

    if not is_vercel_cron and not has_secret:
        return JsonResponse({"error": "forbidden"}, status=403)

    # Nombre total restant avant traitement
    remaining_before = AdMedia.objects.filter(has_watermark=False).count()
    if remaining_before == 0:
        return JsonResponse({"ok": True, "processed": 0, "remaining": 0})

    batch = list(AdMedia.objects.filter(has_watermark=False)[:10])
    processed = 0
    errors = 0
    t0 = _time.monotonic()

    for media in batch:
        # Stopper si on approche 50 secondes (Vercel function timeout ~60s)
        if _time.monotonic() - t0 > 50:
            break
        try:
            media._watermark_applied = False
            result = media._add_watermark_and_thumbnail()
            if result:
                media.save(update_fields=["image", "thumbnail", "has_watermark"])
                processed += 1
            else:
                errors += 1
        except Exception as exc:
            import logging as _logging
            _logging.getLogger(__name__).warning("cron_apply_watermarks media=%s : %s", media.pk, exc)
            errors += 1

    remaining_after = AdMedia.objects.filter(has_watermark=False).count()
    return JsonResponse({
        "ok": True,
        "processed": processed,
        "errors": errors,
        "remaining": remaining_after,
    })
