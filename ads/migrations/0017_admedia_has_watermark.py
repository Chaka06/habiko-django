from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("ads", "0016_favorite"),
    ]

    operations = [
        migrations.AddField(
            model_name="admedia",
            name="has_watermark",
            field=models.BooleanField(
                default=False,
                help_text="Filigrane appliqué sur cette image",
            ),
        ),
    ]
