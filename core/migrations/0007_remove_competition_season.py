# Generated by Django 5.0.6 on 2024-07-06 15:57

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ("core", "0006_alter_competition_options_competition_created_and_more"),
    ]

    operations = [
        migrations.RemoveField(
            model_name="competition",
            name="season",
        ),
    ]
