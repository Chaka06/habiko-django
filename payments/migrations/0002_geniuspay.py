"""
Migration 0002 : Passage de PawaPay à GeniusPay.

Changements :
- Suppression des champs phone, correspondent, pawapay_response
- Ajout de geniuspay_reference, gateway_response
- Mise à jour des choix de type (standard/boost/bundle) et des montants
- Ajout d'un index sur geniuspay_reference
"""
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("payments", "0001_initial"),
    ]

    operations = [
        # 1. Supprimer les anciens index qui référencent deposit_id
        #    (ils seront recréés à la fin si nécessaire)

        # 2. Supprimer les champs PawaPay
        migrations.RemoveField(model_name="payment", name="phone"),
        migrations.RemoveField(model_name="payment", name="correspondent"),
        migrations.RemoveField(model_name="payment", name="pawapay_response"),

        # 3. Ajouter les nouveaux champs GeniusPay
        migrations.AddField(
            model_name="payment",
            name="geniuspay_reference",
            field=models.CharField(
                blank=True,
                default="",
                max_length=50,
                verbose_name="Référence GeniusPay",
            ),
        ),
        migrations.AddField(
            model_name="payment",
            name="gateway_response",
            field=models.JSONField(blank=True, default=dict),
        ),

        # 4. Mettre à jour les choix du champ type
        migrations.AlterField(
            model_name="payment",
            name="type",
            field=models.CharField(
                choices=[
                    ("standard", "Annonce standard (600 FCFA / 5 jours)"),
                    ("boost",    "Boost premium (1 100 FCFA — tête de liste 2h/jour)"),
                    ("bundle",   "Standard + Boost (1 500 FCFA / 5 jours)"),
                ],
                max_length=10,
                verbose_name="Type",
            ),
        ),

        # 5. Mettre à jour les choix du champ status (ajouter cancelled)
        migrations.AlterField(
            model_name="payment",
            name="status",
            field=models.CharField(
                choices=[
                    ("pending",   "En attente de confirmation"),
                    ("completed", "Paiement confirmé"),
                    ("failed",    "Paiement échoué"),
                    ("cancelled", "Paiement annulé"),
                ],
                default="pending",
                max_length=10,
                verbose_name="Statut",
            ),
        ),

        # 6. Ajouter l'index sur geniuspay_reference
        migrations.AddIndex(
            model_name="payment",
            index=models.Index(
                fields=["geniuspay_reference"],
                name="payment_gp_ref_idx",
            ),
        ),
    ]
