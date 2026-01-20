#!/bin/bash
set -e

echo "=========================================="
echo "Starting HABIKO application setup..."
echo "=========================================="

# Exécuter les migrations avec retry en cas d'erreur de connexion
echo ""
echo "Step 1: Running database migrations..."
MAX_RETRIES=5
RETRY_COUNT=0
while [ $RETRY_COUNT -lt $MAX_RETRIES ]; do
    if python manage.py migrate --noinput; then
        echo "✓ Migrations completed successfully"
        break
    else
        RETRY_COUNT=$((RETRY_COUNT + 1))
        if [ $RETRY_COUNT -lt $MAX_RETRIES ]; then
            echo "⚠ Migration failed, retrying in 5 seconds... (attempt $RETRY_COUNT/$MAX_RETRIES)"
            sleep 5
        else
            echo "✗ Migration failed after $MAX_RETRIES attempts!"
            echo "Checking database connection..."
            python manage.py dbshell --command="SELECT 1;" || echo "Cannot connect to database"
            exit 1
        fi
    fi
done

# Créer le Site Django si nécessaire
echo ""
echo "Step 2: Setting up Django Site..."
python manage.py shell << 'PYTHON_EOF'
import os
import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'kiaba.settings')
django.setup()

from django.contrib.sites.models import Site
from django.conf import settings

try:
    site, created = Site.objects.get_or_create(
        id=settings.SITE_ID,
        defaults={
            "domain": "ci-habiko.com",
            "name": "HABIKO",
        }
    )
    if not created and site.domain != "ci-habiko.com":
        site.domain = "ci-habiko.com"
        site.name = "HABIKO"
        site.save()
    print(f"✓ Site configured: {site.domain} (ID: {site.id})")
except Exception as e:
    print(f"✗ Error setting up site: {e}")
    import traceback
    traceback.print_exc()
PYTHON_EOF

# Vérifier que le dossier media existe et est accessible
echo ""
echo "Step 3: Checking media directory..."
if [ -d "/app/media" ]; then
    echo "✓ Media directory exists: /app/media"
    ls -la /app/media | head -5 || echo "⚠ Cannot list media directory"
else
    echo "⚠ Media directory /app/media does not exist, creating..."
    mkdir -p /app/media
    chmod 755 /app/media
fi

# Vérifier la configuration
echo ""
echo "Step 4: Checking Django configuration..."
python manage.py check --deploy || {
    echo "⚠ Django check found some issues, but continuing..."
}

# Démarrer Gunicorn
echo ""
echo "=========================================="
echo "Starting Gunicorn server..."
echo "=========================================="
exec gunicorn kiaba.wsgi:application --bind 0.0.0.0:${PORT:-10000} --workers 2 --timeout 120 --access-logfile - --error-logfile - --log-level info

