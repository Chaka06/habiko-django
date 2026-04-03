from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ("payments", "0004_new_payment_types"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="PromoCodeUsage",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("code", models.CharField(max_length=50, verbose_name="Code promo")),
                ("discount_applied", models.PositiveIntegerField(default=0, verbose_name="Réduction appliquée (FCFA)")),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                (
                    "ad",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="promo_usages",
                        to="ads.ad",
                        verbose_name="Annonce",
                    ),
                ),
                (
                    "user",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="promo_usages",
                        to=settings.AUTH_USER_MODEL,
                        verbose_name="Utilisateur",
                    ),
                ),
            ],
            options={
                "verbose_name": "Utilisation code promo",
                "verbose_name_plural": "Utilisations codes promo",
                "unique_together": {("code", "user")},
            },
        ),
    ]
