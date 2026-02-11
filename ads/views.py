from django.shortcuts import render, get_object_or_404
from django.http import HttpRequest, HttpResponse, JsonResponse
from django.db.models import Q, F
from django.core.paginator import Paginator
from django.views.decorators.http import require_POST
from django.views.decorators.csrf import ensure_csrf_cookie
from .models import Ad, City


def ad_list(request: HttpRequest) -> HttpResponse:
    qs = (
        Ad.objects.filter(status=Ad.Status.APPROVED)
        .select_related("city", "user", "user__profile")
        .prefetch_related("media")
        .order_by("-is_premium", "-is_urgent", "-created_at")
    )
    city = request.GET.get("city")
    category = request.GET.get("category")
    provider = request.GET.get("provider")
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
    q = request.GET.get("q", "").strip()
    if q:
        q_search = Q(title__icontains=q) | Q(description_sanitized__icontains=q)
        for sub in Ad.SUBCATEGORY_CHOICES:
            if q.lower() in sub.lower():
                q_search |= Q(subcategories__contains=[sub])
        qs = qs.filter(q_search)

    # Pagination - 10 annonces par page
    paginator = Paginator(qs, 10)
    page_number = request.GET.get("page")
    page_obj = paginator.get_page(page_number)

    # Cache des villes (elles changent rarement)
    from django.core.cache import cache
    cities = cache.get("all_cities")
    if cities is None:
        cities = list(City.objects.all())
        cache.set("all_cities", cities, 3600)  # 1 heure

    from core.context_processors import CACHE_KEY_TOTAL_ADS, CACHE_TTL
    total_approved_ads = cache.get(CACHE_KEY_TOTAL_ADS)
    if total_approved_ads is None:
        total_approved_ads = Ad.objects.filter(status=Ad.Status.APPROVED).count()
        cache.set(CACHE_KEY_TOTAL_ADS, total_approved_ads, CACHE_TTL)
    return render(
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
            "total_approved_ads": total_approved_ads,
        },
    )


def search_suggestions(request: HttpRequest) -> JsonResponse:
    """Retourne des suggestions de recherche (catégories, sous-catégories, termes des annonces)."""
    q = (request.GET.get("q") or "").strip()[:80]
    if len(q) < 2:
        return JsonResponse({"suggestions": []})

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

    return JsonResponse({"suggestions": suggestions[:15]})


def ad_detail(request: HttpRequest, slug: str) -> HttpResponse:
    ad = get_object_or_404(
        Ad.objects.select_related("city", "user", "user__profile")
        .prefetch_related("media"),
        slug=slug,
        status=Ad.Status.APPROVED
    )

    # Annonces similaires : même catégorie et même ville, exclure l'annonce actuelle
    similar_ads = (
        Ad.objects.filter(status=Ad.Status.APPROVED, category=ad.category, city=ad.city)
        .exclude(id=ad.id)
        .select_related("city", "user", "user__profile")
        .prefetch_related("media")
        .order_by("-created_at")[:5]
    )

    # Si pas assez d'annonces similaires, ajouter d'autres annonces de la même catégorie
    if len(similar_ads) < 5:
        additional_ads = (
            Ad.objects.filter(status=Ad.Status.APPROVED, category=ad.category)
            .exclude(id=ad.id)
            .exclude(id__in=[a.id for a in similar_ads])
            .select_related("city", "user", "user__profile")
            .prefetch_related("media")
            .order_by("-created_at")[: 5 - len(similar_ads)]
        )
        similar_ads = list(similar_ads) + list(additional_ads)

    return render(request, "ads/detail.html", {"ad": ad, "similar_ads": similar_ads})


@require_POST
@ensure_csrf_cookie
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


# Create your views here.
