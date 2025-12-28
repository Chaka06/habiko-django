from django.shortcuts import render, get_object_or_404
from django.http import HttpRequest, HttpResponse
from django.db.models import Q
from django.core.paginator import Paginator
from .models import Ad, City


def ad_list(request: HttpRequest) -> HttpResponse:
    qs = (
        Ad.objects.filter(status=Ad.Status.APPROVED)
        .select_related("city", "user")
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
    q = request.GET.get("q")
    if q:
        qs = qs.filter(Q(title__icontains=q) | Q(description_sanitized__icontains=q))

    # Pagination - 10 annonces par page
    paginator = Paginator(qs, 10)
    page_number = request.GET.get("page")
    page_obj = paginator.get_page(page_number)

    cities = City.objects.all()
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
        },
    )


def ad_detail(request: HttpRequest, slug: str) -> HttpResponse:
    ad = get_object_or_404(
        Ad.objects.select_related("city", "user"), slug=slug, status=Ad.Status.APPROVED
    )

    # Annonces similaires : même catégorie et même ville, exclure l'annonce actuelle
    similar_ads = (
        Ad.objects.filter(status=Ad.Status.APPROVED, category=ad.category, city=ad.city)
        .exclude(id=ad.id)
        .select_related("city", "user")
        .order_by("-created_at")[:5]
    )

    # Si pas assez d'annonces similaires, ajouter d'autres annonces de la même catégorie
    if similar_ads.count() < 5:
        additional_ads = (
            Ad.objects.filter(status=Ad.Status.APPROVED, category=ad.category)
            .exclude(id=ad.id)
            .exclude(id__in=[a.id for a in similar_ads])
            .select_related("city", "user")
            .order_by("-created_at")[: 5 - similar_ads.count()]
        )
        similar_ads = list(similar_ads) + list(additional_ads)

    return render(request, "ads/detail.html", {"ad": ad, "similar_ads": similar_ads})


# Create your views here.
