from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("payments", "0005_promocodeusage"),
    ]

    operations = [
        migrations.CreateModel(
            name="PromoCode",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("code", models.CharField(max_length=50, unique=True, verbose_name="Code")),
                ("discount_percent", models.PositiveSmallIntegerField(verbose_name="Réduction (%)")),
                ("active", models.BooleanField(default=True, verbose_name="Actif")),
                ("expires_at", models.DateTimeField(blank=True, null=True, verbose_name="Expire le")),
                ("max_uses", models.PositiveIntegerField(
                    blank=True, null=True,
                    help_text="Nombre max d'utilisations au total. Vide = illimité.",
                    verbose_name="Max utilisations",
                )),
                ("created_at", models.DateTimeField(auto_now_add=True)),
            ],
            options={
                "verbose_name": "Code promo",
                "verbose_name_plural": "Codes promo",
            },
        ),
    ]
