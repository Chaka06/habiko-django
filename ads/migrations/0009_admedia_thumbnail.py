from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("ads", "0008_add_performance_indexes"),
    ]

    operations = [
        migrations.AddField(
            model_name="admedia",
            name="thumbnail",
            field=models.ImageField(
                upload_to="ads/thumbnails/", blank=True, null=True
            ),
        ),
    ]

