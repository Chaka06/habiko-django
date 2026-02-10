from django.http import HttpResponse
from django.shortcuts import render


def robots_txt(_: object) -> HttpResponse:
    lines = [
        "# KIABA Rencontres - ci-kiaba.com",
        "User-agent: *",
        "Allow: /",
        "Allow: /ads",
        "Allow: /ads/",
        "Allow: /legal/",
        "Allow: /static/",
        "Allow: /media/",
        "Disallow: /admin/",
        "Disallow: /auth/",
        "Disallow: /accounts/",
        "Disallow: /post/",
        "Disallow: /dashboard/",
        "Disallow: /age-gate/",
        "Disallow: /edit/",
        "Disallow: /report/",
        "",
        "# Sitemap (index principal ; les sections sont listées dedans)",
        "Sitemap: https://ci-kiaba.com/sitemap.xml",
    ]
    return HttpResponse("\n".join(lines), content_type="text/plain; charset=utf-8")


def google_verification(_: object) -> HttpResponse:
    """Serve Google Search Console verification file"""
    return HttpResponse(
        "google-site-verification: googleb96ecc9cfd50e4a1.html",
        content_type="text/html; charset=utf-8",
    )
