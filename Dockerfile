FROM python:3.12-slim
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1
WORKDIR /app
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential libpq-dev \
    && rm -rf /var/lib/apt/lists/*
COPY requirements.txt ./
RUN pip install --no-cache-dir -U pip && \
    pip install --no-cache-dir -r requirements.txt && \
    pip install --no-cache-dir -i https://test.pypi.org/simple/ cinetpay-sdk==0.1.1
COPY . .
CMD ["sh", "-c", "python manage.py migrate --noinput && python setup_site.py && gunicorn kiaba.wsgi:application --bind 0.0.0.0:${PORT:-8000} --workers 2 --timeout 120"]
