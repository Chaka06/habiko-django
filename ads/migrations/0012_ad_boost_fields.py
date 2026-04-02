from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("ads", "0011_add_covering_indexes"),
    ]

    operations = [
        migrations.AddField(
            model_name="ad",
            name="is_boosted",
            field=models.BooleanField(
                default=False,
                help_text="Boost acheté (remontée quotidienne)",
            ),
        ),
        migrations.AddField(
            model_name="ad",
            name="boost_expires_at",
            field=models.DateTimeField(
                blank=True,
                null=True,
                help_text="Date d'expiration du boost acheté",
            ),
        ),
    ]
