# isort:skip_file
"""
Entry point for Vercel serverless deployment.
Vercel expects a variable named `app` for Python WSGI applications.
"""
import os
import sys
import logging

logger = logging.getLogger(__name__)

# Ajouter le répertoire racine au path pour que Django trouve le projet
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "kiaba.settings")

from django.core.wsgi import get_wsgi_application

app = get_wsgi_application()

# ─── Migrations au démarrage (cold start) ───────────────────────────────────
# Le build Vercel essaie de lancer migrate --noinput, mais la connexion Supabase
# (IPv6-only sur db.xxx.supabase.co) peut être inaccessible depuis l'environnement
# de build → les migrations ne s'appliquent pas → colonnes manquantes → 500.
# On relance migrate ici (cold start uniquement, ~1-2s) pour rattraper les migrations
# non appliquées. Cela ne ralentit les requêtes que lors du premier démarrage
# d'une nouvelle instance Vercel.
_MIGRATIONS_DONE = False


def _run_pending_migrations():
    """Applique les migrations en attente. Silencieux si déjà à jour."""
    global _MIGRATIONS_DONE
    if _MIGRATIONS_DONE:
        return
    _MIGRATIONS_DONE = True
    try:
        from django.db import connection
        from django.db.migrations.executor import MigrationExecutor
        executor = MigrationExecutor(connection)
        targets = executor.loader.graph.leaf_nodes()
        plan = executor.migration_plan(targets)
        if plan:
            logger.info("Vercel cold start: %d migrations en attente → migrate --noinput", len(plan))
            from django.core.management import call_command
            call_command("migrate", "--noinput", verbosity=0)
            logger.info("Migrations appliquées avec succès au démarrage.")
        else:
            logger.debug("Vercel cold start: aucune migration en attente.")
    except Exception as exc:
        # Ne pas faire planter l'app si les migrations échouent — l'erreur sera
        # loggée et les vues elles-mêmes retourneront 500 avec un message clair.
        logger.error("Erreur lors des migrations au démarrage Vercel : %s", exc)


_run_pending_migrations()
