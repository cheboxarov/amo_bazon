# Generated by Django 5.1 on 2024-08-23 08:40

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ("bazon", "0007_alter_contractor_phone_alter_contractor_type"),
    ]

    operations = [
        migrations.RenameField(
            model_name="contractor",
            old_name="amo_lead_id",
            new_name="amo_id",
        ),
    ]
