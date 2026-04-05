from django.db import migrations


def create_kiaba2_promo(apps, schema_editor):
    PromoCode = apps.get_model("payments", "PromoCode")
    PromoCode.objects.get_or_create(
        code="KIABA#2",
        defaults={
            "discount_percent": 10,
            "active": True,
            "max_uses": None,   # illimité globalement — la contrainte unique_together
                                # sur PromoCodeUsage limite à 1 usage par compte
        },
    )


def reverse_func(apps, schema_editor):
    PromoCode = apps.get_model("payments", "PromoCode")
    PromoCode.objects.filter(code="KIABA#2").delete()


class Migration(migrations.Migration):

    dependencies = [
        ("payments", "0006_promocode"),
    ]

    operations = [
        migrations.RunPython(create_kiaba2_promo, reverse_func),
    ]
