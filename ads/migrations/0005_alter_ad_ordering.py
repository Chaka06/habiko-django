# Generated manually for Ad model ordering update

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('ads', '0004_ad_boost_fields'),
    ]

    operations = [
        migrations.AlterModelOptions(
            name='ad',
            options={'ordering': ['-is_premium', '-is_urgent', '-created_at']},
        ),
    ]


