from django.shortcuts import render, get_object_or_404
from django.http import HttpRequest, HttpResponse, JsonResponse
from django.contrib.auth.decorators import login_required
from django.db.models import Q, F, Case, When, Value, IntegerField
from django.core.cache import cache
from django.core.paginator import Paginator
from django.views.decorators.http import require_POST, require_GET
from django.views.decorators.cache import cache_page
from django.views.decorators.csrf import csrf_exempt
from .models import Ad, City, Favorite
from core.context_processors import get_ad_list_version

AD_LIST_CACHE_TTL = 900  # 15 min


@require_GET
def ad_list(request: HttpRequest) -> HttpResponse:
    city = request.GET.get("city", "")
    category = request.GET.get("category", "")
    provider = request.GET.get("provider", "")
    page = request.GET.get("page", "1")
    q = request.GET.get("q", "").strip()

    # Les recherches libres (?q=…) sont uniques : pas de cache pour ne pas le polluer.
    # Les pages de navigation (city/category/page) sont mises en cache avec une clé
    # versionnée — invalider la version suffit à rafraîchir toutes les pages d'un coup.
    cache_key = None
    if not q:
        version = get_ad_list_version()
        cache_key = f"ad_list:v{version}:{city}:{category}:{provider}:{page}"
        cached = cache.get(cache_key)
        if cached is not None:
            return cached

    qs = (
        Ad.objects.filter(
            status__in=[Ad.Status.APPROVED, Ad.Status.EXPIRED],
            image_processing_done=True,
        )
        .annotate(
            is_expired=Case(
                When(status=Ad.Status.EXPIRED, then=Value(1)),
                default=Value(0),
                output_field=IntegerField(),
            )
        )
        .select_related("city", "user", "user__profile")
        .prefetch_related("media")
        .order_by("is_expired", "-is_premium", "-is_urgent", "-created_at")
    )
    selected_city = None
    selected_category = None

    if city:
        try:
            selected_city = City.objects.get(slug=city)
            qs = qs.filter(city__slug=city)
        except City.DoesNotExist:
            pass
    if category:
        selected_category = category
        qs = qs.filter(category=category)
    if provider:
        if provider.isdigit():
            qs = qs.filter(user_id=int(provider))
        else:
            qs = qs.filter(user__username=provider)
    if q:
        q_search = Q(title__icontains=q) | Q(description_sanitized__icontains=q)
        for sub in Ad.SUBCATEGORY_CHOICES:
            if q.lower() in sub.lower():
                q_search |= Q(subcategories__contains=[sub])
        qs = qs.filter(q_search)

    paginator = Paginator(qs, 10)
    page_obj = paginator.get_page(page)

    cities = cache.get("all_cities")
    if cities is None:
        cities = list(City.objects.all())
        cache.set("all_cities", cities, 86400)  # 24h

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
        },
    )

    if cache_key is not None:
        cache.set(cache_key, response, AD_LIST_CACHE_TTL)

    return response


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


@cache_page(120)  # 2 min par annonce (contenu stable)
def ad_detail(request: HttpRequest, slug: str) -> HttpResponse:
    # Annonce archivée/expirée → 410 Gone (signal fort pour Google : désindexer cette URL)
    if Ad.objects.filter(slug=slug, status=Ad.Status.ARCHIVED).exists():
        from django.template.loader import render_to_string
        return HttpResponse(
            render_to_string("core/404.html", {"reason": "expired"}, request=request),
            status=410,
            content_type="text/html",
        )

    ad = get_object_or_404(
        Ad.objects.filter(status=Ad.Status.APPROVED, image_processing_done=True)
        .select_related("city", "user", "user__profile")
        .prefetch_related("media"),
        slug=slug,
    )

    # Annonces similaires : une seule requête (même catégorie, priorité même ville)
    similar_ads = (
        Ad.objects.filter(status=Ad.Status.APPROVED, image_processing_done=True, category=ad.category)
        .exclude(id=ad.id)
        .select_related("city", "user", "user__profile")
        .prefetch_related("media")
        .annotate(same_city=Case(When(city_id=ad.city_id, then=Value(1)), default=Value(0), output_field=IntegerField()))
        .order_by("-same_city", "-created_at")[:5]
    )

    return render(request, "ads/detail.html", {"ad": ad, "similar_ads": similar_ads})


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
