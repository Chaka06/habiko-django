FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential libpq-dev \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt ./
RUN pip install --no-cache-dir -U pip && \
    pip install --no-cache-dir -r requirements.txt

# Créer un utilisateur non-root pour limiter la surface d'attaque
RUN addgroup --system appgroup && adduser --system --ingroup appgroup --no-create-home appuser

COPY . .

# Donner la propriété des fichiers à l'utilisateur applicatif
RUN chown -R appuser:appgroup /app

USER appuser

# Healthcheck : vérifie que le serveur répond (adapté à l'endpoint /health/ si disponible)
HEALTHCHECK --interval=30s --timeout=10s --start-period=20s --retries=3 \
    CMD python -c "import urllib.request, os; urllib.request.urlopen('http://localhost:' + os.environ.get('PORT', '8000') + '/')" || exit 1

CMD ["sh", "-c", "python manage.py migrate --noinput && python setup_site.py && gunicorn kiaba.wsgi:application --bind 0.0.0.0:${PORT:-8000} --workers 2 --timeout 120"]
