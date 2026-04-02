from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ("ads", "0014_ad_boost_interval_hours"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="Report",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("reason", models.CharField(
                    choices=[
                        ("spam", "Spam / annonce dupliquée"),
                        ("fake", "Fausse annonce / arnaque"),
                        ("underage", "Personne mineure"),
                        ("violence", "Violence / contenu choquant"),
                        ("prostitution", "Prostitution / traite"),
                        ("other", "Autre"),
                    ],
                    max_length=20,
                )),
                ("details", models.TextField(blank=True, max_length=1000)),
                ("ip_address", models.GenericIPAddressField(blank=True, null=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("reviewed", models.BooleanField(default=False)),
                ("ad", models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name="reports",
                    to="ads.ad",
                )),
                ("reporter", models.ForeignKey(
                    blank=True,
                    null=True,
                    on_delete=django.db.models.deletion.SET_NULL,
                    related_name="submitted_reports",
                    to=settings.AUTH_USER_MODEL,
                )),
            ],
            options={"ordering": ["-created_at"]},
        ),
        migrations.AddIndex(
            model_name="report",
            index=models.Index(fields=["ad", "reviewed"], name="moderation_report_ad_reviewed_idx"),
        ),
    ]
