from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("payments", "0003_renewal_type"),
    ]

    operations = [
        migrations.AlterField(
            model_name="payment",
            name="type",
            field=models.CharField(
                choices=[
                    ("standard",   "Annonce standard (1 000 FCFA / 5 jours)"),
                    ("boost",      "Boost seul (800 FCFA — tête toutes les 2h)"),
                    ("bundle",     "Standard + Boost (1 800 FCFA / 5 jours)"),
                    ("fortnight",  "Pack 15 jours + Boost (3 500 FCFA / tête 4h)"),
                    ("monthly",    "Pack mensuel + Boost (6 500 FCFA / tête 3h)"),
                    ("renew_15",   "Renouvellement 15 jours (1 000 FCFA)"),
                    ("renew_15b",  "Renouvellement 15 jours + Boost (2 500 FCFA)"),
                    ("renew_mon",  "Renouvellement 1 mois (2 000 FCFA)"),
                    ("renew_monb", "Renouvellement 1 mois + Boost (4 000 FCFA)"),
                ],
                max_length=12,
                verbose_name="Type",
            ),
        ),
    ]
