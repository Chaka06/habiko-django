from django.db import migrations, models
import django.utils.timezone


class Migration(migrations.Migration):

    dependencies = [
        ("ads", "0017_admedia_has_watermark"),
    ]

    operations = [
        migrations.AddField(
            model_name="ad",
            name="bumped_at",
            field=models.DateTimeField(
                null=True,
                blank=True,
                help_text="Dernière remontée en tête de liste (auto-bump pour les annonces boostées)",
                db_index=True,
            ),
        ),
        # Initialiser bumped_at = created_at pour toutes les annonces existantes
        migrations.RunSQL(
            sql="UPDATE ads_ad SET bumped_at = created_at WHERE bumped_at IS NULL;",
            reverse_sql="UPDATE ads_ad SET bumped_at = NULL;",
        ),
    ]
