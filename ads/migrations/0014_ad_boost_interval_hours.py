from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("ads", "0013_ad_expiry_notification_flags"),
    ]

    operations = [
        migrations.AddField(
            model_name="ad",
            name="boost_interval_hours",
            field=models.PositiveSmallIntegerField(
                default=2,
                help_text="Intervalle de remontée en tête (heures) : 2h, 3h ou 4h selon forfait",
            ),
        ),
    ]
