# Generated by Django 4.1.3 on 2023-05-16 15:20

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion
import uuid


class Migration(migrations.Migration):
    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="Competition",
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
                ("data_source_id", models.PositiveIntegerField(unique=True)),
                ("name", models.CharField(max_length=100)),
                ("season", models.PositiveIntegerField(verbose_name="Temporada")),
            ],
            options={
                "verbose_name": "competição",
                "verbose_name_plural": "competições",
                "ordering": ("name",),
            },
        ),
        migrations.CreateModel(
            name="Guess",
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
                ("home_goals", models.PositiveIntegerField()),
                ("away_goals", models.PositiveIntegerField()),
                ("score", models.PositiveIntegerField(default=0)),
                ("consolidated", models.BooleanField(default=False)),
            ],
            options={
                "verbose_name": "palpite",
                "verbose_name_plural": "palpites",
            },
        ),
        migrations.CreateModel(
            name="Guesser",
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
                (
                    "receive_notifications",
                    models.BooleanField(
                        default=True, verbose_name="Receber notificações"
                    ),
                ),
            ],
        ),
        migrations.CreateModel(
            name="Team",
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
                ("name", models.CharField(max_length=50)),
                ("code", models.CharField(blank=True, max_length=3, null=True)),
            ],
            options={
                "verbose_name": "equipe",
                "verbose_name_plural": "equipes",
                "ordering": ("name",),
            },
        ),
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
        migrations.CreateModel(
            name="GuessPool",
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
                (
                    "created",
                    models.DateTimeField(auto_now_add=True, verbose_name="Criação"),
                ),
                (
                    "modified",
                    models.DateTimeField(auto_now=True, verbose_name="Atualização"),
                ),
                (
                    "uuid",
                    models.UUIDField(
                        default=uuid.uuid4,
                        editable=False,
                        unique=True,
                        verbose_name="Identificador público",
                    ),
                ),
                (
                    "name",
                    models.CharField(max_length=100, unique=True, verbose_name="nome"),
                ),
                ("slug", models.SlugField(unique=True)),
                ("private", models.BooleanField(default=True, verbose_name="privado")),
                (
                    "new_matches",
                    models.BooleanField(default=False, verbose_name="novas partidas"),
                ),
                (
                    "updated_matches",
                    models.BooleanField(
                        default=False, verbose_name="partidas atualizadas"
                    ),
                ),
                (
                    "competitions",
                    models.ManyToManyField(
                        blank=True,
                        related_name="pools",
                        to="core.competition",
                        verbose_name="competições",
                    ),
                ),
                (
                    "guessers",
                    models.ManyToManyField(
                        blank=True,
                        related_name="pools",
                        to="core.guesser",
                        verbose_name="palpiteiros",
                    ),
                ),
                (
                    "guesses",
                    models.ManyToManyField(
                        blank=True, related_name="pools", to="core.guess"
                    ),
                ),
                (
                    "owner",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="own_pools",
                        to="core.guesser",
                    ),
                ),
                (
                    "teams",
                    models.ManyToManyField(
                        blank=True,
                        related_name="pools",
                        to="core.team",
                        verbose_name="times",
                    ),
                ),
            ],
            options={
                "verbose_name": "bolão",
                "verbose_name_plural": "bolões",
            },
        ),
        migrations.AddField(
            model_name="guesser",
            name="supported_team",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                to="core.team",
                verbose_name="Time do coração",
            ),
        ),
        migrations.AddField(
            model_name="guesser",
            name="user",
            field=models.OneToOneField(
                on_delete=django.db.models.deletion.CASCADE, to=settings.AUTH_USER_MODEL
            ),
        ),
        migrations.AddField(
            model_name="guess",
            name="guesser",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.CASCADE,
                related_name="guesses",
                to="core.guesser",
            ),
        ),
        migrations.AddField(
            model_name="guess",
            name="match",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.CASCADE,
                related_name="guesses",
                to="core.match",
            ),
        ),
        migrations.AddField(
            model_name="competition",
            name="teams",
            field=models.ManyToManyField(related_name="competitions", to="core.team"),
        ),
    ]
