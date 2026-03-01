# Ajout d'index couvrants (covering indexes) pour les requêtes de liste d'annonces.
# Ces index sont conçus pour la requête principale :
#   Ad.objects.filter(status=APPROVED, image_processing_done=True)
#              .order_by("-is_premium", "-is_urgent", "-created_at")
# Avec filtres optionnels city et category.
# PostgreSQL peut parcourir l'index seul sans toucher la table (index-only scan).

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("ads", "0010_ad_image_processing_done"),
    ]

    operations = [
        # Index couvrant la requête principale (status + image_done → tri premium/urgent/date)
        migrations.AddIndex(
            model_name="ad",
            index=models.Index(
                fields=["status", "image_processing_done", "is_premium", "is_urgent", "created_at"],
                name="ad_main_list_idx",
            ),
        ),
        # Index pour la liste filtrée par ville
        migrations.AddIndex(
            model_name="ad",
            index=models.Index(
                fields=["status", "image_processing_done", "city", "created_at"],
                name="ad_city_list_idx",
            ),
        ),
        # Index pour la liste filtrée par catégorie
        migrations.AddIndex(
            model_name="ad",
            index=models.Index(
                fields=["status", "image_processing_done", "category", "created_at"],
                name="ad_category_list_idx",
            ),
        ),
    ]
