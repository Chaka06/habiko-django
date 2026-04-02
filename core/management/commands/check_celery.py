from django.core.management.base import BaseCommand
from django.conf import settings


class Command(BaseCommand):
    help = "Check Celery configuration"

    def handle(self, *args, **options):
        self.stdout.write("Checking Celery configuration...")
        self.stdout.write(f"REDIS_URL: {settings.CELERY_BROKER_URL}")
        self.stdout.write(f"CELERY_BROKER_URL: {getattr(settings, 'CELERY_BROKER_URL', 'Not set')}")
        self.stdout.write(
            f"CELERY_RESULT_BACKEND: {getattr(settings, 'CELERY_RESULT_BACKEND', 'Not set')}"
        )
        self.stdout.write(
            f"CELERY_TASK_ALWAYS_EAGER: {getattr(settings, 'CELERY_TASK_ALWAYS_EAGER', 'Not set')}"
        )

        if getattr(settings, "CELERY_TASK_ALWAYS_EAGER", False):
            self.stdout.write(
                self.style.SUCCESS("✅ Celery is in EAGER mode (tasks execute synchronously)")
            )
        else:
            self.stdout.write(
                self.style.WARNING("⚠️ Celery is in ASYNC mode (tasks execute asynchronously)")
            )
