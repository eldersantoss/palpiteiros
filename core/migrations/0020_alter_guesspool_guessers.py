# Generated by Django 4.1.3 on 2023-04-12 11:23

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("core", "0019_alter_rodada_label_alter_rodada_pool"),
    ]

    operations = [
        migrations.AlterField(
            model_name="guesspool",
            name="guessers",
            field=models.ManyToManyField(
                blank=True, related_name="pools", to="core.palpiteiro"
            ),
        ),
    ]