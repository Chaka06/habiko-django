from django.http import HttpResponse
from django.shortcuts import render


def robots_txt(_: object) -> HttpResponse:
    # Format standard : pas de BOM, fin par newline. Sitemap URL absolue valide.
    content = (
        "User-agent: *\n"
        "Disallow: /admin/\n"
        "Disallow: /auth/\n"
        "Disallow: /accounts/\n"
        "Disallow: /post/\n"
        "Disallow: /dashboard/\n"
        "Disallow: /age-gate/\n"
        "Disallow: /edit/\n"
        "Disallow: /report/\n"
        "\n"
        "Sitemap: https://ci-kiaba.com/sitemap.xml\n"
    )
    response = HttpResponse(
        content.encode("utf-8"),
        content_type="text/plain; charset=utf-8",
    )
    response["Cache-Control"] = "public, max-age=3600"
    return response


def google_verification(_: object) -> HttpResponse:
    """Serve Google Search Console verification file"""
    return HttpResponse(
        "google-site-verification: googleb96ecc9cfd50e4a1.html",
        content_type="text/html; charset=utf-8",
    )
