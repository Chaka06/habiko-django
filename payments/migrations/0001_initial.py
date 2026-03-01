import uuid
import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ("ads", "0012_ad_boost_fields"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="Payment",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                (
                    "deposit_id",
                    models.UUIDField(default=uuid.uuid4, editable=False, unique=True),
                ),
                (
                    "type",
                    models.CharField(
                        choices=[
                            ("standard", "Annonce standard (500 FCFA / 5 jours)"),
                            ("boost", "Boost premium (700 FCFA / 7 jours + remontée 2h/jour)"),
                        ],
                        max_length=10,
                        verbose_name="Type",
                    ),
                ),
                ("amount", models.PositiveIntegerField(verbose_name="Montant (FCFA)")),
                (
                    "status",
                    models.CharField(
                        choices=[
                            ("pending", "En attente de confirmation"),
                            ("completed", "Paiement confirmé"),
                            ("failed", "Paiement échoué"),
                        ],
                        default="pending",
                        max_length=10,
                        verbose_name="Statut",
                    ),
                ),
                ("phone", models.CharField(max_length=20, verbose_name="Numéro mobile money")),
                (
                    "correspondent",
                    models.CharField(
                        help_text="MTN_MOMO_CIV ou ORANGE_CIV",
                        max_length=30,
                        verbose_name="Opérateur",
                    ),
                ),
                ("pawapay_response", models.JSONField(blank=True, default=dict)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("completed_at", models.DateTimeField(blank=True, null=True)),
                (
                    "user",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="payments",
                        to=settings.AUTH_USER_MODEL,
                        verbose_name="Utilisateur",
                    ),
                ),
                (
                    "ad",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="payments",
                        to="ads.ad",
                        verbose_name="Annonce",
                    ),
                ),
            ],
            options={
                "verbose_name": "Paiement",
                "verbose_name_plural": "Paiements",
                "ordering": ["-created_at"],
            },
        ),
        migrations.AddIndex(
            model_name="payment",
            index=models.Index(fields=["deposit_id"], name="payment_deposit_idx"),
        ),
        migrations.AddIndex(
            model_name="payment",
            index=models.Index(fields=["user", "status"], name="payment_user_status_idx"),
        ),
        migrations.AddIndex(
            model_name="payment",
            index=models.Index(fields=["ad", "type"], name="payment_ad_type_idx"),
        ),
    ]
