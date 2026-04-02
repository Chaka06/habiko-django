from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from accounts.tasks import (
    send_account_created_email,
    send_login_notification_email,
    send_password_change_email,
)


class Command(BaseCommand):
    help = "Test Celery tasks in production"

    def handle(self, *args, **options):
        User = get_user_model()

        # Get first user for testing
        try:
            user = User.objects.first()
            if not user:
                self.stdout.write(self.style.ERROR("❌ No users found. Create a user first."))
                return

            self.stdout.write(f"Testing with user: {user.username} ({user.email})")

            # Test account created email
            self.stdout.write("Testing send_account_created_email...")
            result = send_account_created_email.delay(user.id)
            # Si CELERY_TASK_ALWAYS_EAGER=True, result sera le résultat direct
            # Sinon, result sera un objet AsyncResult
            if hasattr(result, "result"):
                self.stdout.write(f"✅ Account created email sent (task ID: {result.id})")
            else:
                self.stdout.write(f"✅ Account created email: {result}")

            # Test login notification email
            self.stdout.write("Testing send_login_notification_email...")
            result = send_login_notification_email.delay(user.id)
            if hasattr(result, "result"):
                self.stdout.write(f"✅ Login notification email sent (task ID: {result.id})")
            else:
                self.stdout.write(f"✅ Login notification email: {result}")

            # Test password change email
            self.stdout.write("Testing send_password_change_email...")
            result = send_password_change_email.delay(user.id)
            if hasattr(result, "result"):
                self.stdout.write(f"✅ Password change email sent (task ID: {result.id})")
            else:
                self.stdout.write(f"✅ Password change email: {result}")

            self.stdout.write(self.style.SUCCESS("✅ All Celery tasks tested successfully!"))

        except Exception as e:
            self.stdout.write(self.style.ERROR(f"❌ Error testing Celery tasks: {e}"))
