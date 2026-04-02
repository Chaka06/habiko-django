from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("ads", "0009_admedia_thumbnail"),
    ]

    operations = [
        migrations.AddField(
            model_name="ad",
            name="image_processing_done",
            field=models.BooleanField(
                default=True,
                help_text="True une fois toutes les images traitées (filigrane + miniature). Les annonces n'apparaissent en liste qu'une fois True.",
            ),
        ),
        migrations.AddIndex(
            model_name="ad",
            index=models.Index(
                fields=["status", "image_processing_done"],
                name="ad_list_ready_idx",
            ),
        ),
    ]
