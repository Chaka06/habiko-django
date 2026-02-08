"""
Entry point for Vercel serverless deployment.
Vercel expects a variable named `app` for Python WSGI applications.
"""
import os
import sys

# Ajouter le répertoire racine au path pour que Django trouve le projet
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "kiaba.settings")

from django.core.wsgi import get_wsgi_application

app = get_wsgi_application()
