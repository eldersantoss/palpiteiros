# Generated by Django 4.1.3 on 2023-01-25 19:43

import core.models
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("core", "0007_remove_palpiteiro_pontuacao_alter_palpite_palpiteiro_and_more"),
    ]

    operations = [
        migrations.AlterModelOptions(
            name="equipe",
            options={"ordering": ("nome",)},
        ),
        migrations.AlterField(
            model_name="rodada",
            name="label",
            field=models.CharField(
                default=core.models.Rodada._gerar_label_default,
                editable=False,
                max_length=50,
            ),
        ),
    ]