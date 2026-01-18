from django.core.management.base import BaseCommand
from django.core.mail import send_mail
from django.conf import settings


class Command(BaseCommand):
    help = "Test email configuration in production"

    def add_arguments(self, parser):
        parser.add_argument(
            "--to",
            type=str,
            default="test@example.com",
            help="Email address to send test to",
        )

    def handle(self, *args, **options):
        to_email = options["to"]

        self.stdout.write(f"Testing email configuration...")
        self.stdout.write(f"EMAIL_BACKEND: {settings.EMAIL_BACKEND}")
        self.stdout.write(f"DEFAULT_FROM_EMAIL: {settings.DEFAULT_FROM_EMAIL}")
        self.stdout.write(f"SERVER_EMAIL: {settings.SERVER_EMAIL}")

        try:
            send_mail(
                subject="Test Email from HABIKO",
                message="This is a test email from HABIKO production server.",
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[to_email],
                fail_silently=False,
            )
            self.stdout.write(self.style.SUCCESS(f"✅ Test email sent successfully to {to_email}"))
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"❌ Failed to send email: {e}"))
