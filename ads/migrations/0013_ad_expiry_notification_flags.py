from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("ads", "0012_ad_boost_fields"),
    ]

    operations = [
        migrations.AddField(
            model_name="ad",
            name="expiry_notified_24h",
            field=models.BooleanField(default=False, help_text="Email d'avertissement J-1 déjà envoyé"),
        ),
        migrations.AddField(
            model_name="ad",
            name="expiry_notified_1h",
            field=models.BooleanField(default=False, help_text="Email d'avertissement H-1 déjà envoyé"),
        ),
    ]
