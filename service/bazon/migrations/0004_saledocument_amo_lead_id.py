# Generated by Django 5.1 on 2024-08-21 08:15

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('bazon', '0003_saledocument'),
    ]

    operations = [
        migrations.AddField(
            model_name='saledocument',
            name='amo_lead_id',
            field=models.PositiveIntegerField(blank=True, null=True),
        ),
    ]