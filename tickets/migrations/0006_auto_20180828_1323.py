# Generated by Django 2.1 on 2018-08-28 18:23

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('tickets', '0005_auto_20180828_0826'),
    ]

    operations = [
        migrations.AlterField(
            model_name='agent',
            name='email',
            field=models.CharField(max_length=64, unique=True),
        ),
        migrations.AlterField(
            model_name='agent',
            name='name',
            field=models.CharField(max_length=64, unique=True),
        ),
    ]
