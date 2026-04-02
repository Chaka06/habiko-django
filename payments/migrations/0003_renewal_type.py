from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("payments", "0002_geniuspay"),
    ]

    operations = [
        migrations.AlterField(
            model_name="payment",
            name="type",
            field=models.CharField(
                choices=[
                    ("standard", "Annonce standard (600 FCFA / 5 jours)"),
                    ("boost", "Boost premium (1 100 FCFA — tête de liste 2h/jour)"),
                    ("bundle", "Standard + Boost (1 500 FCFA / 5 jours)"),
                    ("renewal", "Renouvellement (600 FCFA / +5 jours)"),
                ],
                max_length=10,
                verbose_name="Type",
            ),
        ),
    ]
