from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("ads", "0014_ad_boost_interval_hours"),
    ]

    operations = [
        migrations.AlterField(
            model_name="ad",
            name="status",
            field=models.CharField(
                choices=[
                    ("draft", "Draft"),
                    ("pending", "Pending"),
                    ("approved", "Approved"),
                    ("rejected", "Rejected"),
                    ("archived", "Archived"),
                    ("expired", "Expirée"),
                ],
                default="draft",
                max_length=10,
            ),
        ),
    ]
