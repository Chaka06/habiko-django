from django.http import HttpResponse
from django.shortcuts import render
from django.conf import settings


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


def ads_txt(_: object) -> HttpResponse:
    """
    Fichier ads.txt pour Google AdSense (à la racine du domaine).
    Ligne exacte attendue par AdSense : google.com, pub-XXXXXXXXXX, DIRECT, f08c47fec0942fa0
    """
    pub_id = getattr(settings, "ADSENSE_PUBLISHER_ID", "").strip()
    if not pub_id:
        content = "# AdSense non configuré : définir ADSENSE_PUBLISHER_ID dans les variables d'environnement\n"
    else:
        # AdSense attend "pub-XXXXXXXXXX" dans ads.txt (sans le préfixe "ca-")
        ads_txt_id = pub_id.replace("ca-pub-", "pub-", 1) if pub_id.startswith("ca-pub-") else pub_id
        content = f"google.com, {ads_txt_id}, DIRECT, f08c47fec0942fa0\n"
    response = HttpResponse(content, content_type="text/plain; charset=utf-8")
    response["Cache-Control"] = "public, max-age=3600"
    return response
