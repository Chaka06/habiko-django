from django.core.management.base import BaseCommand
from django.core.management import call_command
from django.contrib.sitemaps import ping_google


class Command(BaseCommand):
    help = "Generate sitemap and ping search engines"

    def add_arguments(self, parser):
        parser.add_argument(
            "--ping",
            action="store_true",
            help="Ping Google with the sitemap",
        )

    def handle(self, *args, **options):
        self.stdout.write("Generating sitemap...")

        # Generate sitemap
        call_command("collectstatic", "--noinput")

        self.stdout.write("Sitemap generated successfully!")
        self.stdout.write("Sitemap available at: https://ci-habiko.com/sitemap.xml")

        if options["ping"]:
            try:
                ping_google()
                self.stdout.write(self.style.SUCCESS("✅ Successfully pinged Google with sitemap"))
            except Exception as e:
                self.stdout.write(self.style.WARNING(f"⚠️ Failed to ping Google: {e}"))

        self.stdout.write(self.style.SUCCESS("🎉 Sitemap generation completed!"))
