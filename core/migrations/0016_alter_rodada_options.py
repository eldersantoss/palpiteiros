# Generated by Django 4.1.3 on 2023-04-08 15:50

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ("core", "0015_alter_rodada_options"),
    ]

    operations = [
        migrations.AlterModelOptions(
            name="rodada",
            options={
                "ordering": ("-created",),
                "verbose_name": "Rodada",
                "verbose_name_plural": "Rodadas",
            },
        ),
    ]
