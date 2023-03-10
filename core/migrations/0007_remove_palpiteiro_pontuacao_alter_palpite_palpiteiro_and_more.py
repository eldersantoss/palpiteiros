# Generated by Django 4.1.3 on 2023-01-10 15:32

import core.models
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ("core", "0006_alter_partida_data_hora_alter_partida_rodada"),
    ]

    operations = [
        migrations.RemoveField(
            model_name="palpiteiro",
            name="pontuacao",
        ),
        migrations.AlterField(
            model_name="palpite",
            name="palpiteiro",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.CASCADE,
                related_name="palpites",
                to="core.palpiteiro",
            ),
        ),
        migrations.AlterField(
            model_name="palpite",
            name="partida",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.CASCADE,
                related_name="palpites",
                to="core.partida",
            ),
        ),
        migrations.AlterField(
            model_name="palpite",
            name="pontuacao",
            field=models.PositiveIntegerField(default=0),
        ),
        migrations.AlterField(
            model_name="rodada",
            name="label",
            field=models.CharField(
                default=core.models.Rodada._gerar_label_default, max_length=50
            ),
        ),
    ]
