# Ajout d'index sur les champs de recherche fréquents pour améliorer les performances.
# - CustomUser.phone_e164 : utilisé dans les vérifications d'unicité
# - Profile.whatsapp_e164, Profile.phone2_e164 : idem
# - Transaction (user+status) et (status+created_at) : filtrage paiements

import django.core.validators
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("accounts", "0007_profile_phone2_e164"),
    ]

    operations = [
        # Index sur CustomUser.phone_e164
        migrations.AlterField(
            model_name="customuser",
            name="phone_e164",
            field=models.CharField(
                blank=True,
                db_index=True,
                help_text="Phone number in E.164 format, e.g., +2250700000000",
                max_length=20,
                null=True,
                validators=[
                    django.core.validators.RegexValidator(
                        message="Entrez un numéro au format E.164 (ex: +225XXXXXXXXXX)",
                        regex="^\\+[1-9]\\d{1,14}$",
                    )
                ],
            ),
        ),
        # Index sur Profile.whatsapp_e164
        migrations.AlterField(
            model_name="profile",
            name="whatsapp_e164",
            field=models.CharField(
                blank=True,
                db_index=True,
                max_length=20,
                null=True,
                validators=[
                    django.core.validators.RegexValidator(
                        message="Entrez un numéro au format E.164 (ex: +225XXXXXXXXXX)",
                        regex="^\\+[1-9]\\d{1,14}$",
                    )
                ],
            ),
        ),
        # Index sur Profile.phone2_e164
        migrations.AlterField(
            model_name="profile",
            name="phone2_e164",
            field=models.CharField(
                blank=True,
                db_index=True,
                help_text="Second phone number for ads (optional). Shown with primary on ad contact.",
                max_length=20,
                null=True,
                validators=[
                    django.core.validators.RegexValidator(
                        message="Entrez un numéro au format E.164 (ex: +225XXXXXXXXXX)",
                        regex="^\\+[1-9]\\d{1,14}$",
                    )
                ],
            ),
        ),
        # Index composite Transaction (user, status) et (status, created_at)
        migrations.AddIndex(
            model_name="transaction",
            index=models.Index(
                fields=["user", "status"], name="transaction_user_status_idx"
            ),
        ),
        migrations.AddIndex(
            model_name="transaction",
            index=models.Index(
                fields=["status", "created_at"], name="transaction_status_date_idx"
            ),
        ),
    ]
