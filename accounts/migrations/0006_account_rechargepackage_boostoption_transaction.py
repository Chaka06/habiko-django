# Generated manually for credit system

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0005_emailotp'),
        ('ads', '0003_alter_city_options'),
    ]

    operations = [
        migrations.CreateModel(
            name='RechargePackage',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=100)),
                ('amount', models.DecimalField(decimal_places=2, help_text='Montant en FCFA', max_digits=10)),
                ('ads_included', models.PositiveIntegerField(help_text='Nombre d\'annonces incluses')),
                ('credit_amount', models.DecimalField(decimal_places=2, default=0, help_text='Montant de crédit ajouté au compte pour booster', max_digits=10)),
                ('free_boosters', models.PositiveIntegerField(default=0, help_text='Nombre de boosters gratuits (pack 15000 FCFA = 2)')),
                ('is_premium', models.BooleanField(default=False, help_text='Pack premium (20000 FCFA)')),
                ('is_active', models.BooleanField(default=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
            ],
            options={
                'verbose_name': 'Formule de recharge',
                'verbose_name_plural': 'Formules de recharge',
                'ordering': ['amount'],
            },
        ),
        migrations.CreateModel(
            name='BoostOption',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('boost_type', models.CharField(choices=[('premium', 'Premium'), ('prolongation', 'Prolongation'), ('urgent', 'Urgent')], max_length=20)),
                ('name', models.CharField(max_length=100)),
                ('duration_days', models.PositiveIntegerField(help_text='Durée en jours')),
                ('price', models.DecimalField(decimal_places=2, help_text='Prix en FCFA', max_digits=10)),
                ('is_active', models.BooleanField(default=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
            ],
            options={
                'verbose_name': 'Option de boost',
                'verbose_name_plural': 'Options de boost',
                'ordering': ['boost_type', 'duration_days'],
            },
        ),
        migrations.CreateModel(
            name='Account',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('balance', models.DecimalField(decimal_places=2, default=0, help_text='Solde en FCFA', max_digits=10)),
                ('free_ads_remaining', models.PositiveIntegerField(default=0, help_text='Nombre d\'annonces gratuites restantes')),
                ('ads_remaining', models.PositiveIntegerField(default=0, help_text='Nombre d\'annonces restantes du pack acheté')),
                ('is_premium', models.BooleanField(default=False, help_text='Compte premium (15 annonces premium)')),
                ('premium_ads_remaining', models.PositiveIntegerField(default=0, help_text='Nombre d\'annonces premium restantes')),
                ('free_boosters_remaining', models.PositiveIntegerField(default=0, help_text='Nombre de boosters gratuits restants (pack 15000 FCFA)')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('user', models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name='account', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'verbose_name': 'Compte',
                'verbose_name_plural': 'Comptes',
            },
        ),
        migrations.CreateModel(
            name='Transaction',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('transaction_type', models.CharField(choices=[('recharge', 'Recharge'), ('boost', 'Boost'), ('refund', 'Remboursement')], max_length=20)),
                ('amount', models.DecimalField(decimal_places=2, max_digits=10)),
                ('status', models.CharField(choices=[('pending', 'En attente'), ('completed', 'Complétée'), ('failed', 'Échouée'), ('cancelled', 'Annulée')], default='pending', max_length=20)),
                ('cinetpay_transaction_id', models.CharField(blank=True, max_length=100, null=True)),
                ('description', models.TextField(blank=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('ad', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='transactions', to='ads.ad')),
                ('boost_option', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to='accounts.boostoption')),
                ('recharge_package', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to='accounts.rechargepackage')),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='transactions', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'verbose_name': 'Transaction',
                'verbose_name_plural': 'Transactions',
                'ordering': ['-created_at'],
            },
        ),
    ]


