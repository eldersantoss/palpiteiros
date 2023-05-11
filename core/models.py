from datetime import datetime
from typing import Iterable, Literal
from uuid import uuid4

import requests
from django.conf import settings
from django.contrib import admin
from django.db import models, transaction
from django.db.models import Q, Sum
from django.db.models.functions import Coalesce
from django.urls import reverse_lazy
from django.utils import timezone
from django.utils.text import slugify
from django.utils.translation import gettext as _


class TimeStampedModel(models.Model):
    created = models.DateTimeField("Criação", auto_now_add=True)
    modified = models.DateTimeField("Atualização", auto_now=True)

    class Meta:
        abstract = True


class Team(models.Model):
    data_source_id = models.PositiveIntegerField(blank=True, null=True)
    name = models.CharField(max_length=50)
    code = models.CharField(max_length=3, blank=True, null=True)

    class Meta:
        verbose_name = "equipe"
        verbose_name_plural = "equipes"
        ordering = ("name",)

    def __str__(self) -> str:
        return self.name

    def logo_url(self):
        return f"https://media.api-sports.io/football/teams/{self.data_source_id}.png"


class Competition(models.Model):
    data_source_id = models.PositiveIntegerField(unique=True)
    name = models.CharField(max_length=100)
    season = models.PositiveIntegerField("Temporada")
    teams = models.ManyToManyField(Team, related_name="competitions")

    class Meta:
        verbose_name = "competição"
        verbose_name_plural = "competições"
        ordering = ("name",)

    def __str__(self) -> str:
        return self.name

    def logo_url(self) -> str:
        return f"https://media.api-sports.io/football/leagues/{self.data_source_id}.png"

    def get_teams(self):
        source_url = f"https://{settings.FOOTBALL_API_HOST}/teams"
        headers = {
            "x-rapidapi-key": settings.FOOTBALL_API_KEY,
            "x-rapidapi-host": settings.FOOTBALL_API_HOST,
        }
        params = {"league": self.data_source_id, "season": self.season}

        # TODO: tratar requests.exceptions.ConnectionError:
        response = (
            requests.get(source_url, headers=headers, params=params)
            .json()
            .get("response")
        )

        teams = []
        for data in response:
            data_source_id = data["team"]["id"]
            name = data["team"]["name"]
            code = data["team"]["code"]

            team, _ = Team.objects.get_or_create(
                data_source_id=data_source_id,
                name=name,
                code=code,
            )
            teams.append(team)

        self.teams.set(teams)

        return teams

    def get_new_matches(self, days_ahead: int):
        api_url = f"https://{settings.FOOTBALL_API_HOST}/fixtures"
        headers = {
            "x-rapidapi-key": settings.FOOTBALL_API_KEY,
            "x-rapidapi-host": settings.FOOTBALL_API_HOST,
        }
        params = {
            "timezone": settings.TIME_ZONE,
            "league": self.data_source_id,
            "season": self.season,
            "from": str(timezone.now().date()),
            "to": str(timezone.now().date() + timezone.timedelta(days=days_ahead)),
            "status": "NS",
        }

        # TODO: tratar requests.exceptions.ConnectionError:
        response = requests.get(api_url, headers=headers, params=params)
        json_data = response.json()
        json_data_response = json_data["response"]

        matches = []
        for data in json_data_response:
            data_source_id = data["fixture"]["id"]
            date_time = timezone.datetime.fromisoformat(data["fixture"]["date"])
            status = data["fixture"]["status"]["short"]
            home_team_source_id = data["teams"]["home"]["id"]
            away_team_source_id = data["teams"]["away"]["id"]

            home_team = Team.objects.get(data_source_id=home_team_source_id)
            away_team = Team.objects.get(data_source_id=away_team_source_id)

            match, created = Partida.objects.get_or_create(
                data_source_id=data_source_id,
                competition=self,
                status=status,
                mandante=home_team,
                visitante=away_team,
                data_hora=date_time,
            )
            if created:
                matches.append(match)

        return matches

    def update_matches(self, days_from: int | None, days_ahead: int | None):
        api_url = f"https://{settings.FOOTBALL_API_HOST}/fixtures"
        headers = {
            "x-rapidapi-key": settings.FOOTBALL_API_KEY,
            "x-rapidapi-host": settings.FOOTBALL_API_HOST,
        }
        today = timezone.now().date()
        from_ = today - timezone.timedelta(days=days_from or 1)
        to = today + timezone.timedelta(days=days_ahead or 0)
        params = {
            "timezone": settings.TIME_ZONE,
            "league": self.data_source_id,
            "season": self.season,
            "from": str(from_),
            "to": str(to),
            "status": "-".join(Partida.IN_PROGRESS_AND_FINISHED_STATUS),
        }

        # TODO: tratar requests.exceptions.ConnectionError:
        response = requests.get(api_url, headers=headers, params=params)
        json_data = response.json()
        json_data_response = json_data["response"]

        matches = []
        for data in json_data_response:
            data_source_id = data["fixture"]["id"]
            status = data["fixture"]["status"]["short"]
            elapsed = data["fixture"]["status"]["elapsed"]
            home_goals = data["goals"]["home"]
            away_goals = data["goals"]["away"]

            try:
                match = Partida.objects.exclude(status__in=Partida.FINISHED_STATUS).get(
                    data_source_id=data_source_id
                )
            except Partida.DoesNotExist:
                continue

            match.update_status(status, elapsed)
            match.gols_mandante = home_goals
            match.gols_visitante = away_goals
            match.save()
            matches.append(match)

        return matches

    def create_public_pool(self):
        name = f"{self.name} {self.season}"
        slug = slugify(name)
        owner = Palpiteiro.objects.get(usuario__username=settings.ADMIN_USERNAME)
        private = False

        pool, created = GuessPool.objects.get_or_create(
            name=name,
            slug=slug,
            owner=owner,
            private=private,
        )

        if created:
            pool.competitions.add(self)
            return pool

        return None


class Partida(models.Model):
    NOT_STARTED = "NS"
    FIRST_HALF = "1H"
    HALFTIME = "HT"
    SECOND_HALF = "2H"
    FINSHED = "FT"
    FINSHED_AFTER_EXTRA_TIME = "AET"
    FINSHED_AFTER_PENALTYS = "PEN"

    IN_PROGRESS_STATUS = [FIRST_HALF, HALFTIME, SECOND_HALF]

    FINISHED_STATUS = [FINSHED, FINSHED_AFTER_EXTRA_TIME, FINSHED_AFTER_PENALTYS]

    IN_PROGRESS_AND_FINISHED_STATUS = [*IN_PROGRESS_STATUS, *FINISHED_STATUS]

    STATUS_CHOICES = (
        (NOT_STARTED, "Não iniciada"),
        (FIRST_HALF, "1º tempo"),
        (HALFTIME, "Intervalo"),
        (SECOND_HALF, "2º tempo"),
        (FINSHED, "Encerrada"),
        (FINSHED_AFTER_EXTRA_TIME, "Encerrada após prorrogação"),
        (FINSHED_AFTER_PENALTYS, "Encerrada após penalidades"),
    )

    MINUTES_BEFORE_START_MATCH = 30

    HOURS_BEFORE_OPEN_TO_GUESSES = 48

    data_source_id = models.PositiveIntegerField(blank=True, null=True)
    competition = models.ForeignKey(
        Competition,
        verbose_name="Competição",
        on_delete=models.PROTECT,
        related_name="matches",
    )
    status = models.CharField(max_length=4, choices=STATUS_CHOICES, default=NOT_STARTED)
    mandante = models.ForeignKey(
        Team,
        on_delete=models.CASCADE,
        related_name="partidas_mandante",
    )
    visitante = models.ForeignKey(
        Team,
        on_delete=models.CASCADE,
        related_name="partidas_visitante",
    )
    data_hora = models.DateTimeField("Data e hora")
    gols_mandante = models.PositiveIntegerField(blank=True, null=True)
    gols_visitante = models.PositiveIntegerField(blank=True, null=True)
    pontuacao_dobrada = models.BooleanField(default=False)

    class Meta:
        verbose_name = "partida"
        verbose_name_plural = "partidas"
        ordering = ("data_hora",)
        unique_together = ["mandante", "visitante", "data_hora"]

    def __str__(self):
        return f"{self.mandante.name} x {self.visitante.name}"

    def save(self, *args, **kwargs):
        is_update = self.id is not None
        super().save(*args, **kwargs)
        if is_update:
            self.evaluate_and_consolidate_guesses()
            self.set_updated_matches_flag_for_involved_pools()
        else:
            self.set_new_macthes_flag_for_involved_pools()

    def update_status(
        self,
        new_status: str,
        elapsed_time: int,
        match_time_limit_minutes=150,
    ):
        self.status = new_status

        match_time_limit = self.data_hora + timezone.timedelta(
            minutes=match_time_limit_minutes
        )
        match_broke_limit_time = timezone.now() >= match_time_limit

        REGULAR_MATCH_DURATION = 90

        if (
            match_broke_limit_time
            and elapsed_time >= REGULAR_MATCH_DURATION
            and self.status == Partida.SECOND_HALF
        ):
            self.status = Partida.FINISHED_STATUS

    def is_finished(self) -> bool:
        return self.status in self.FINISHED_STATUS

    def evaluate_and_consolidate_guesses(self):
        with transaction.atomic():
            for guess in self.palpites.all():
                guess.evaluate_and_consolidate()

    def set_updated_matches_flag_for_involved_pools(self):
        GuessPool.toggle_flag_value("updated_matches", self.get_pools(), True)

    def set_new_macthes_flag_for_involved_pools(self):
        GuessPool.toggle_flag_value("new_matches", self.get_pools(), True)

    @property
    def result_str(self):
        return (
            f"{self.gols_mandante} x {self.gols_visitante}"
            if self.gols_mandante is not None and self.gols_visitante is not None
            else None
        )

    @admin.display(
        boolean=True,
        description="Aberta para palpites?",
    )
    def open_to_guesses(self):
        return (
            self.data_hora
            > timezone.now()
            + timezone.timedelta(minutes=self.MINUTES_BEFORE_START_MATCH)
        ) and (
            self.data_hora
            <= timezone.now()
            + timezone.timedelta(hours=self.HOURS_BEFORE_OPEN_TO_GUESSES)
        )

    def get_pools(self):
        """Return all pools with this instance of Match is involved"""

        pools_with_competition_as_pool_member = self.competition.pools.all()
        pools_with_home_team_as_pool_member = self.mandante.pools.all()
        pools_with_away_team_as_pool_member = self.visitante.pools.all()

        return pools_with_competition_as_pool_member.union(
            pools_with_home_team_as_pool_member,
            pools_with_away_team_as_pool_member,
        )

    def get_guess_by_guesser(self, guesser: "Palpiteiro"):
        try:
            return self.palpites.get(palpiteiro=guesser)
        except Palpite.DoesNotExist:
            return None

    def pending_guess(self, guesser: "Palpiteiro"):
        return not self.palpites.filter(palpiteiro=guesser).exists()


class Palpiteiro(models.Model):
    usuario = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)

    def get_involved_pools(self):
        return self.own_pools.all().union(self.pools.all()).order_by("name")

    @classmethod
    def get_who_should_be_notified_by_email(cls):
        """Returns guessers that should be notified by email"""
        return cls.objects.exclude(usuario__email="").exclude(pools__isnull=True)

    def get_involved_pools_with_new_matches(self):
        """Returns pools with new matches that this guesser is involved
        with"""
        return self.pools.filter(new_matches=True)

    def get_involved_pools_with_updated_matches(self):
        """Returns pools with updated matches that this guesser is involved
        with"""
        return self.pools.filter(updated_matches=True)

    def __str__(self) -> str:
        return f"{self.usuario.get_full_name()} ({self.usuario.username})"


class Palpite(models.Model):
    palpiteiro = models.ForeignKey(
        Palpiteiro,
        on_delete=models.CASCADE,
        related_name="palpites",
    )
    partida = models.ForeignKey(
        Partida,
        on_delete=models.CASCADE,
        related_name="palpites",
    )
    gols_mandante = models.PositiveIntegerField()
    gols_visitante = models.PositiveIntegerField()
    pontuacao = models.PositiveIntegerField(default=0)
    contabilizado = models.BooleanField(default=False)

    class Meta:
        verbose_name = "palpite"
        verbose_name_plural = "palpites"

    def __str__(self) -> str:
        return (
            f"{self.partida.mandante.name} {self.gols_mandante}"
            + " x "
            + f"{self.gols_visitante} {self.partida.visitante.name}"
        )

    def get_score(self) -> int:
        if not self.contabilizado:
            self.evaluate_and_consolidate()
        return self.pontuacao

    def evaluate_and_consolidate(self):
        if self.partida.result_str is not None:
            self.pontuacao = self._evaluate()

            if self.partida.is_finished():
                self.contabilizado = True

            self.save()

    @property
    def result_str(self) -> str:
        return f"{self.gols_mandante} x {self.gols_visitante}"

    def _evaluate(self):
        ACERTO_DE_GOLS_MANDANTE = self.gols_mandante == self.partida.gols_mandante
        ACERTO_DE_GOLS_VISITANTE = self.gols_visitante == self.partida.gols_visitante
        ACERTO_MANDANTE_VENCEDOR = (self.gols_mandante > self.gols_visitante) and (
            self.partida.gols_mandante > self.partida.gols_visitante
        )
        ACERTO_VISITANTE_VENCEDOR = (self.gols_mandante < self.gols_visitante) and (
            self.partida.gols_mandante < self.partida.gols_visitante
        )
        ACERTO_EMPATE = (self.gols_mandante == self.gols_visitante) and (
            self.partida.gols_mandante == self.partida.gols_visitante
        )
        ACERTO_PARCIAL = ACERTO_MANDANTE_VENCEDOR or ACERTO_VISITANTE_VENCEDOR
        ACERTO_PARCIAL_COM_GOLS = ACERTO_PARCIAL and (
            ACERTO_DE_GOLS_MANDANTE or ACERTO_DE_GOLS_VISITANTE
        )
        ACERTO_SOMENTE_GOLS = (
            ACERTO_DE_GOLS_MANDANTE or ACERTO_DE_GOLS_VISITANTE
        ) and not ACERTO_PARCIAL
        ACERTO_CRAVADO = ACERTO_DE_GOLS_MANDANTE and ACERTO_DE_GOLS_VISITANTE

        PONTUACAO_ACERTO_CRAVADO = 10
        PONTUACAO_ACERTO_PARCIAL_COM_GOLS = 5
        PONTUACAO_ACERTO_EMPATE = 5
        PONTUACAO_ACERTO_PARCIAL = 3
        PONTUACAO_ACERTO_SOMENTE_GOLS = 1

        if ACERTO_CRAVADO:
            score = PONTUACAO_ACERTO_CRAVADO
        elif ACERTO_PARCIAL_COM_GOLS:
            score = PONTUACAO_ACERTO_PARCIAL_COM_GOLS
        elif ACERTO_EMPATE:
            score = PONTUACAO_ACERTO_EMPATE
        elif ACERTO_PARCIAL:
            score = PONTUACAO_ACERTO_PARCIAL
        elif ACERTO_SOMENTE_GOLS:
            score = PONTUACAO_ACERTO_SOMENTE_GOLS
        else:
            score = 0

        if self.partida.pontuacao_dobrada:
            score *= 2

        return score


class GuessPool(TimeStampedModel):
    MAX_MATCHES_TO_SHOW_INTO_RANKING = 50

    uuid = models.UUIDField(
        "identificador público",
        unique=True,
        editable=False,
        default=uuid4,
    )
    name = models.CharField("nome", max_length=100, unique=True)
    slug = models.SlugField(unique=True)
    owner = models.ForeignKey(
        Palpiteiro,
        related_name="own_pools",
        on_delete=models.PROTECT,
    )
    private = models.BooleanField(
        "privado",
        default=True,
    )
    guessers = models.ManyToManyField(
        Palpiteiro,
        related_name="pools",
        blank=True,
        verbose_name="palpiteiros",
    )
    competitions = models.ManyToManyField(
        Competition,
        related_name="pools",
        verbose_name="competições",
        blank=True,
    )
    teams = models.ManyToManyField(
        Team,
        related_name="pools",
        verbose_name="times",
        blank=True,
    )
    guesses = models.ManyToManyField(
        Palpite,
        related_name="pools",
        blank=True,
    )
    new_matches = models.BooleanField(
        "novas partidas",
        default=False,
    )
    updated_matches = models.BooleanField(
        "partidas atualizadas",
        default=False,
    )

    class Meta:
        verbose_name = "bolão"
        verbose_name_plural = "bolões"

    def __str__(self) -> str:
        return self.name

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        if not self.guessers.contains(self.owner):
            self.guessers.add(self.owner)

    def get_absolute_url(self):
        return reverse_lazy("core:pool_home", kwargs={"pool_slug": self.slug})

    def get_signin_url(self):
        return reverse_lazy("core:signin_pool", kwargs={"uuid": self.uuid})

    def signin_new_guesser(self, guesser: Palpiteiro):
        self.guessers.add(guesser)

    @admin.display(description="Equipes")
    def number_of_teams(self):
        return self.teams.count()

    @admin.display(description="Palpiteiros")
    def number_of_guessers(self):
        return self.guessers.count()

    def guesser_is_member(self, guesser: Palpiteiro):
        return self.guessers.contains(guesser)

    def get_open_matches(self):
        """Returns matches open to guesses"""

        return self.get_matches().filter(
            data_hora__gt=timezone.now()
            + timezone.timedelta(minutes=Partida.MINUTES_BEFORE_START_MATCH),
            data_hora__lte=timezone.now()
            + timezone.timedelta(hours=Partida.HOURS_BEFORE_OPEN_TO_GUESSES),
        )

    def has_pending_match(self, guesser: Palpiteiro) -> bool:
        matches = self.get_open_matches()
        for match in matches:
            if match.pending_guess(guesser):
                return True
        return False

    @classmethod
    def toggle_flag_value(
        cls,
        flag: Literal["new_matches", "updated_matches"],
        objs: Iterable | None = None,
        desired_value: bool = False,
    ):
        if flag not in ["new_matches", "updated_matches"]:
            raise ValueError(f"flag value must be 'new_matches' or 'updated_matches'")

        pools = objs or (
            cls.objects.filter(new_matches=not desired_value)
            if flag == "new_matches"
            else cls.objects.filter(updated_matches=not desired_value)
        )

        for p in pools:
            setattr(p, flag, desired_value)
        cls.objects.bulk_update(pools, [flag])

    def add_guess_to_pools(self, guess: Palpite, for_all_pools: bool):
        match = guess.partida
        guesser = guess.palpiteiro

        if for_all_pools:
            pools_with_the_match = match.get_pools()
            pools_with_the_guesser = guesser.pools.all()
            pools_with_match_and_guesser = pools_with_the_match.intersection(
                pools_with_the_guesser
            )

            for pool in pools_with_match_and_guesser:
                self._replace_guess_in_pool(guess, pool)

        else:
            self._replace_guess_in_pool(guess)

    def _replace_guess_in_pool(self, guess, pool=None):
        target_pool = pool or self

        with transaction.atomic():
            try:
                old_guess = target_pool.guesses.get(
                    partida=guess.partida,
                    palpiteiro=guess.palpiteiro,
                )
                target_pool.guesses.remove(old_guess)

            except Palpite.DoesNotExist:
                pass

            target_pool.guesses.add(guess)

    @classmethod
    def delete_orphans_guesses(cls):
        """Deletes Palpite instances that are not related with a Pool"""

        return Palpite.objects.exclude(pools__in=cls.objects.all()).delete()

    def get_matches(self):
        """Returns all matches created after this pool that belongs to
        any registered competition or involving registered teams"""

        matches_post_pool_creation = Partida.objects.filter(
            data_hora__gt=self.created,
        )

        competition_or_team_membership = (
            Q(competition__in=self.competitions.all())
            | Q(mandante__in=self.teams.all())
            | Q(visitante__in=self.teams.all())
        )

        return matches_post_pool_creation.filter(competition_or_team_membership)

    def get_guessers_with_score_and_guesses(
        self,
        month: int,
        year: int,
        round_: int,
    ):
        start, end = self._assemble_datetime_period(month, year, round_)
        matches = self.get_finished_or_in_progress_matches_on_period(start, end)
        guessers = self.get_guessers_with_match_scores(matches)

        for guesser in guessers:
            guesser.matches_and_guesses = self._get_guesses_per_matches(
                guesser, matches
            )

        return guessers

    def _assemble_datetime_period(self, month: int, year: int, round_: int):
        base_start = timezone.now().replace(day=1, hour=0, minute=0, second=0)
        base_end = timezone.now().replace(day=1, hour=23, minute=59, second=59)

        # periodo geral (entre data de criação do bolão até data atual)
        if year == 0:
            start = self.created
            end = timezone.now().replace(hour=23, minute=59, second=59)

        else:
            # período anual (todos os meses do ano recebido)
            if month == 0:
                start = base_start.replace(year=year, month=1)
                end = base_end.replace(year=year, month=12, day=31)

            else:
                # período mensal (mes e ano recebidos)
                if round_ == 0:
                    start = base_start.replace(year=year, month=month)
                    end = (
                        base_end.replace(year=year, month=month + 1)
                        if month < 12
                        else base_end.replace(year=year + 1, month=1)
                    ) - timezone.timedelta(days=1)

                else:
                    # período semanal (ano, mes e semanas recebidos)
                    start = timezone.now().fromisocalendar(year, round_, 1)
                    end = (
                        timezone.now()
                        .fromisocalendar(year, round_, 7)
                        .replace(hour=23, minute=59, second=59)
                    )

        return start, end

    def get_finished_or_in_progress_matches_on_period(
        self,
        start: datetime,
        end: datetime,
    ):
        """Returns fininshed or in progress matches with data_hora field
        between start and end"""

        return (
            self.get_matches()
            .filter(status__in=Partida.IN_PROGRESS_AND_FINISHED_STATUS)
            .filter(data_hora__gt=start, data_hora__lte=end)
        )

    def get_guessers_with_match_scores(self, matches: Iterable[Partida]):
        guesses_of_this_pool_in_the_period = Q(palpites__partida__in=matches) & Q(
            palpites__in=self.guesses.all()
        )
        sum_expr = Sum(
            "palpites__pontuacao",
            filter=guesses_of_this_pool_in_the_period,
        )
        return self.guessers.annotate(score=Coalesce(sum_expr, 0)).order_by("-score")

    def _get_guesses_per_matches(self, guesser, matches):
        matches_and_guesses = []

        for match in matches[: self.MAX_MATCHES_TO_SHOW_INTO_RANKING]:
            try:
                guess = self.guesses.get(partida=match, palpiteiro=guesser)

            except Palpite.DoesNotExist:
                guess = None

            matches_and_guesses.append({"match": match, "guess": guess})

        return matches_and_guesses

    def remove_guesser(self, guesser: Palpiteiro):
        self.guesses.remove(*self.guesses.filter(palpiteiro=guesser))
        self.delete_orphans_guesses()
        self.guessers.remove(guesser)

    @admin.display(description="Partidas")
    def number_of_matches(self):
        return self.get_matches().count()
