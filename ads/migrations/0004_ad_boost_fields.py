# Generated manually for boost fields

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('ads', '0003_alter_city_options'),
    ]

    operations = [
        migrations.AddField(
            model_name='ad',
            name='is_premium',
            field=models.BooleanField(default=False, help_text='Annonce premium (en tête de liste)'),
        ),
        migrations.AddField(
            model_name='ad',
            name='premium_until',
            field=models.DateTimeField(blank=True, help_text='Date jusqu\'à laquelle l\'annonce est premium', null=True),
        ),
        migrations.AddField(
            model_name='ad',
            name='is_urgent',
            field=models.BooleanField(default=False, help_text='Annonce urgente (logo urgent)'),
        ),
        migrations.AddField(
            model_name='ad',
            name='urgent_until',
            field=models.DateTimeField(blank=True, help_text='Date jusqu\'à laquelle l\'annonce est urgente', null=True),
        ),
        migrations.AddField(
            model_name='ad',
            name='extended_until',
            field=models.DateTimeField(blank=True, help_text='Date de prolongation de l\'annonce', null=True),
        ),
    ]


