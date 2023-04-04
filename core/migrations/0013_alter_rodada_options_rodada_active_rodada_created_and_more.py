# Generated by Django 4.1.3 on 2023-04-02 16:02

import core.models
from django.db import migrations, models
import django.utils.timezone


class Migration(migrations.Migration):

    dependencies = [
        ("core", "0012_alter_palpite_pontuacao"),
    ]

    operations = [
        migrations.AlterModelOptions(
            name="rodada",
            options={"verbose_name": "Rodada", "verbose_name_plural": "Rodadas"},
        ),
        migrations.AddField(
            model_name="rodada",
            name="active",
            field=models.BooleanField(default=False, verbose_name="Ativa"),
        ),
        migrations.AddField(
            model_name="rodada",
            name="created",
            field=models.DateTimeField(
                auto_now_add=True,
                default=django.utils.timezone.now,
                verbose_name="Criação",
            ),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name="rodada",
            name="modified",
            field=models.DateTimeField(auto_now=True, verbose_name="Atualização"),
        ),
        migrations.AddField(
            model_name="rodada",
            name="slug",
            field=models.SlugField(default=""),
        ),
        migrations.AlterField(
            model_name="rodada",
            name="label",
            field=models.CharField(
                default=core.models.Rodada._gerar_label_default, max_length=100
            ),
        ),
    ]
