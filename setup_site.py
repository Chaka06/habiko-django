#!/usr/bin/env python
"""Script pour configurer le Site Django après les migrations"""
import os
import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "kiaba.settings")
django.setup()

from django.contrib.sites.models import Site
from django.conf import settings
from django.core.management import call_command

try:
    site, created = Site.objects.get_or_create(
        id=settings.SITE_ID,
        defaults={
            "domain": "ci-kiaba.com",
            "name": "KIABA",
        },
    )
    if not created and site.domain != "ci-kiaba.com":
        site.domain = "ci-kiaba.com"
        site.name = "KIABA"
        site.save()
    print(f"✓ Site configured: {site.domain} (ID: {site.id})")

    # Seeder des villes de base sans nécessiter de shell Render payant
    try:
        call_command("seed_cities")
    except Exception as e:
        print(f"✗ Error seeding cities: {e}")
    # Créer un superutilisateur par défaut si nécessaire
    try:
        call_command("create_initial_superuser")
    except Exception as e:
        print(f"✗ Error creating initial superuser: {e}")
except Exception as e:
    print(f"✗ Error setting up site: {e}")
    import traceback

    traceback.print_exc()
    # Ne pas faire échouer le démarrage si le Site existe déjà
    exit(0)

