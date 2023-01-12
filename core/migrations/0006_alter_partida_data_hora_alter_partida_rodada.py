# Generated by Django 4.1.3 on 2022-12-12 21:15

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ("core", "0005_palpite_pontuacao"),
    ]

    operations = [
        migrations.AlterField(
            model_name="partida",
            name="data_hora",
            field=models.DateTimeField(verbose_name="Data e hora"),
        ),
        migrations.AlterField(
            model_name="partida",
            name="rodada",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.CASCADE,
                related_name="partidas",
                to="core.rodada",
            ),
        ),
    ]
