# Generated for second phone on profile (ads contact)

import django.core.validators
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("accounts", "0006_account_rechargepackage_boostoption_transaction"),
    ]

    operations = [
        migrations.AddField(
            model_name="profile",
            name="phone2_e164",
            field=models.CharField(
                blank=True,
                help_text="Second phone number for ads (optional). Shown with primary on ad contact.",
                max_length=20,
                null=True,
                validators=[
                    django.core.validators.RegexValidator(
                        message="Enter a valid E.164 phone.",
                        regex="^\\+[1-9]\\d{1,14}$",
                    )
                ],
            ),
        ),
    ]
