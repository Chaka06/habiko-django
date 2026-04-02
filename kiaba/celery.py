import os
from celery import Celery

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "kiaba.settings")

app = Celery("kiaba")
app.config_from_object("django.conf:settings", namespace="CELERY")
app.autodiscover_tasks()
