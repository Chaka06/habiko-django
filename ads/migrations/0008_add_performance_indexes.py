# Generated manually for performance optimization

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('ads', '0007_add_additional_fields'),
    ]

    operations = [
        migrations.AddIndex(
            model_name='ad',
            index=models.Index(fields=['status', 'is_premium', 'is_urgent', 'created_at'], name='ad_list_idx'),
        ),
        migrations.AddIndex(
            model_name='ad',
            index=models.Index(fields=['status', 'category'], name='ad_category_idx'),
        ),
        migrations.AddIndex(
            model_name='ad',
            index=models.Index(fields=['status', 'city'], name='ad_city_idx'),
        ),
        migrations.AddIndex(
            model_name='ad',
            index=models.Index(fields=['slug'], name='ad_slug_idx'),
        ),
        migrations.AddIndex(
            model_name='ad',
            index=models.Index(fields=['user', 'status'], name='ad_user_status_idx'),
        ),
    ]
