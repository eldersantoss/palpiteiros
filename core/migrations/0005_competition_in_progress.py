# Generated by Django 5.0.6 on 2024-06-27 19:42

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("core", "0004_alter_guesspool_competitions_and_more"),
    ]

    operations = [
        migrations.AddField(
            model_name="competition",
            name="in_progress",
            field=models.BooleanField(default=True, verbose_name="Está em andamento?"),
        ),
    ]
