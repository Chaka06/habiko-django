# isort:skip_file
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

# Appliquer les migrations au cold start (le build Vercel n'a pas toujours accès à la DB).
# Évite l'erreur "socialaccount_socialapp does not exist" sur /auth/login/
try:
    from django.core.management import call_command
    call_command("migrate", "--noinput")
except Exception:
    pass
