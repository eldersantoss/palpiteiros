# Generated by Django 4.1.3 on 2023-05-11 11:02

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [
        ("core", "0002_rename_equipe_team_alter_team_options_and_more"),
    ]

    operations = [
        migrations.CreateModel(
            name="Match",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                ("data_source_id", models.PositiveIntegerField(blank=True, null=True)),
                (
                    "status",
                    models.CharField(
                        choices=[
                            ("NS", "Não iniciada"),
                            ("1H", "1º tempo"),
                            ("HT", "Intervalo"),
                            ("2H", "2º tempo"),
                            ("FT", "Encerrada"),
                            ("AET", "Encerrada após prorrogação"),
                            ("PEN", "Encerrada após penalidades"),
                        ],
                        default="NS",
                        max_length=4,
                    ),
                ),
                ("date_time", models.DateTimeField(verbose_name="Data e hora")),
                ("home_goals", models.PositiveIntegerField(blank=True, null=True)),
                ("away_goals", models.PositiveIntegerField(blank=True, null=True)),
                ("double_score", models.BooleanField(default=False)),
                (
                    "away_team",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="matches_as_away_team",
                        to="core.team",
                    ),
                ),
                (
                    "competition",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="matches",
                        to="core.competition",
                        verbose_name="Competição",
                    ),
                ),
                (
                    "home_team",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="matches_as_home_team",
                        to="core.team",
                    ),
                ),
            ],
            options={
                "verbose_name": "partida",
                "verbose_name_plural": "partidas",
                "ordering": ("date_time",),
                "unique_together": {("home_team", "away_team", "date_time")},
            },
        ),
        migrations.AlterField(
            model_name="palpite",
            name="partida",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.CASCADE,
                related_name="palpites",
                to="core.match",
            ),
        ),
        migrations.DeleteModel(
            name="Partida",
        ),
    ]
