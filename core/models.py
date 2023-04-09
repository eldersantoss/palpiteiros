from datetime import timedelta, datetime

from django.db import models, transaction
from django.conf import settings
from django.contrib import admin
from django.contrib.auth.models import User
from django.utils import timezone
from django.utils.text import slugify
from django.core.exceptions import ValidationError

from .forms import GuessForm


class TimeStampedModel(models.Model):
    created = models.DateTimeField("Criação", auto_now_add=True)
    modified = models.DateTimeField("Atualização", auto_now=True)

    class Meta:
        abstract = True


class Equipe(models.Model):
    nome = models.CharField(max_length=50)
    abreviacao = models.CharField(max_length=3, default="???")

    class Meta:
        verbose_name = "equipe"
        verbose_name_plural = "equipes"
        ordering = ("nome",)

    def __str__(self) -> str:
        return self.nome


class Rodada(TimeStampedModel):
    label = models.CharField(max_length=100)
    slug = models.SlugField()
    active = models.BooleanField("Ativa", default=False)
    pool = models.ForeignKey(
        "GuessPool",
        verbose_name="Bolão",
        on_delete=models.CASCADE,
        related_name="rounds",
        blank=True,
        null=True,
    )

    class Meta:
        ordering = ("-created",)
        verbose_name = "Rodada"
        verbose_name_plural = "Rodadas"
        unique_together = ["slug", "pool"]

    def save(self, *args, **kwargs):
        self.clean()
        self.label = self._generate_label()
        self.slug = slugify(self.label)
        super().save(*args, **kwargs)

    def clean(self) -> None:
        super().clean()
        if (
            self.active
            and Rodada.objects.filter(active=True, pool=self.pool)
            .exclude(id=self.id)
            .exists()
        ):
            raise ValidationError(
                {
                    "active": [
                        "Já existe uma rodada ativa. Desative-a para poder ativar esta."
                    ]
                }
            )

    def _generate_label(self):
        nome_meses = [
            "janeiro",
            "fevereiro",
            "março",
            "abril",
            "maio",
            "junho",
            "julho",
            "agosto",
            "setembro",
            "outubro",
            "novembro",
            "dezembro",
        ]
        mes_atual = timezone.now().month
        ano_atual = timezone.now().year
        numero_rodada = (
            Rodada.objects.filter(created__month=mes_atual, pool=self.pool).count() + 1
        )
        return f"{numero_rodada}ª rodada de {nome_meses[mes_atual - 1]} de {ano_atual}"

    @admin.display(description="Número de partidas")
    def number_of_matches(self) -> int:
        return self.partidas.count()

    @classmethod
    def get_visible_rounds(cls):
        """Filter queryset to exclude inactive future rounds"""
        inactive_future_rounds = models.Q(active=False) & models.Q(
            opening__gt=timezone.now()
        )
        visible_rounds = (
            cls.objects.annotate(opening=models.Min("partidas__data_hora"))
            .exclude(inactive_future_rounds)
            .order_by("-created")
        )
        return visible_rounds

    def get_details(self, logged_user: User) -> list[dict[str, any]]:
        round_details = []
        for guesser in Palpiteiro.objects.all():
            detail = {
                "guesser": guesser,
                "round_score": guesser.get_round_score(self),
                "matches_and_guesses": [],
            }
            for match in self.get_matches():
                guess = (
                    match.get_guess_by_guesser(guesser)
                    if logged_user.palpiteiro == guesser or not match.open_to_guesses()
                    else None
                )
                detail["matches_and_guesses"].append({"match": match, "guess": guess})
            round_details.append(detail)
        round_details.sort(key=lambda e: e["round_score"], reverse=True)
        return round_details

    def get_matches(self) -> models.QuerySet["Partida"]:
        return self.partidas.all()

    def __str__(self) -> str:
        return f"{self.label} do bolão {self.pool}"


class Partida(models.Model):
    rodada = models.ManyToManyField(Rodada, related_name="partidas")
    mandante = models.ForeignKey(
        Equipe,
        on_delete=models.CASCADE,
        related_name="partidas_mandante",
    )
    visitante = models.ForeignKey(
        Equipe,
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
        return f"{self.mandante.nome} x {self.visitante.nome}"

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        for guess in self.palpites.all():
            guess.evaluate_and_consolidate()

    @classmethod
    def have_open_matches_for_any_active_round(cls):
        return cls.objects.filter(
            rodada__active=True,
            data_hora__gt=timezone.now() + timedelta(minutes=30),
        ).exists()

    @classmethod
    def get_closed_matches_with_guesses(cls, guesser: "Palpiteiro"):
        """For each closed match of the the active rounds, it searches
        and appends the guess of the provided guesser, if exists."""

        closed_matches = cls.objects.filter(
            rodada__active=True,
            data_hora__lte=timezone.now() + timedelta(minutes=30),
        )
        for cm in closed_matches:
            try:
                cm.guess = cm.palpites.get(palpiteiro=guesser)
            except Palpite.DoesNotExist:
                cm.guess = None
        return closed_matches

    @classmethod
    def create_update_or_retrieve_guesses_from_your_forms(
        cls,
        guesser: "Palpiteiro",
        post_data: dict = {},
    ):
        """For each open match, if post_data was provided, instantiate
        a form with the post_data and create or update the guess for
        the provided guesser. Otherwise, for GET requests, instantiate
        a clean form or with data from a guess already created for this
        match. Also, appends a guess_form attribute with the instance
        of the created form for all matches."""

        open_matches = cls.objects.filter(
            rodada__active=True,
            data_hora__gt=timezone.now() + timedelta(minutes=30),
        )

        with transaction.atomic():
            for om in open_matches:
                form = GuessForm(post_data, partida=om)
                if form.is_valid():
                    obj, created = om.palpites.get_or_create(
                        palpiteiro=guesser,
                        defaults={
                            "gols_mandante": form.cleaned_data[f"gols_mandante"],
                            "gols_visitante": form.cleaned_data[f"gols_visitante"],
                        },
                    )
                    if not created:
                        obj.gols_mandante = form.cleaned_data[f"gols_mandante"]
                        obj.gols_visitante = form.cleaned_data[f"gols_visitante"]
                        obj.save()

                else:
                    try:
                        guess = om.palpites.get(palpiteiro=guesser)
                        initial_data = {
                            f"gols_mandante_{om.id}": guess.gols_mandante,
                            f"gols_visitante_{om.id}": guess.gols_visitante,
                        }
                    except Palpite.DoesNotExist:
                        initial_data = {}
                    form = GuessForm(initial_data, partida=om)

                om.guess_form = form

        return open_matches

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
        return timezone.now() + timedelta(minutes=30) < self.data_hora

    def get_guess_by_guesser(self, guesser: "Palpiteiro"):
        try:
            return self.palpites.get(palpiteiro=guesser)
        except Palpite.DoesNotExist:
            return None


class Palpiteiro(models.Model):
    usuario = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)

    @classmethod
    def get_ranking(cls, month: int, year: int) -> list["Palpiteiro"]:
        base_start = timezone.now().replace(day=1, hour=0, minute=0, second=0)
        base_end = timezone.now().replace(day=1, hour=23, minute=59, second=59)

        # todos os meses do ano recebido
        if not month and year:
            start = base_start.replace(year=year, month=1)
            end = base_end.replace(year=year, month=12, day=31)

        # periodo geral (entre data da primeira partida registrada até data atual)
        elif not year:
            oldest_match = Partida.objects.first()
            start = timezone.now() if oldest_match is None else oldest_match.data_hora
            end = timezone.now()

        # mes e ano recebidos
        else:
            start = base_start.replace(year=year, month=month)
            end = (
                base_end.replace(year=year, month=month + 1)
                if month < 12
                else base_end.replace(year=year + 1, month=1)
            ) - timedelta(days=1)

        guessers = list(cls.objects.all())
        for guesser in guessers:
            guesser.score = guesser.get_period_score(start, end)
        guessers.sort(key=lambda p: p.score, reverse=True)
        return guessers

    def get_period_score(self, period_start: datetime, period_end: datetime):
        return sum(
            guess.get_score()
            for guess in (
                self.palpites.filter(
                    partida__data_hora__gt=period_start + timedelta(hours=3),
                    partida__data_hora__lt=period_end + timedelta(hours=3),
                )
            )
        )

    def get_round_score(self, round_: "Rodada") -> int:
        return sum(
            guess.get_score()
            for guess in (self.palpites.filter(partida__rodada=round_))
        )

    @admin.display(
        boolean=True,
        description="Palpitou na última rodada",
    )
    def guessed_on_last_round(self):
        last_guess = self.palpites.last()
        last_active_round = Rodada.objects.filter(active=True).first()
        if last_guess is not None:
            return last_guess.partida.rodada == last_active_round
        return False

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
        unique_together = ["palpiteiro", "partida"]

    def __str__(self) -> str:
        return (
            f"{self.partida.mandante.nome} {self.gols_mandante}"
            + " x "
            + f"{self.gols_visitante} {self.partida.visitante.nome}"
        )

    def get_score(self) -> int:
        self.evaluate_and_consolidate()
        return self.pontuacao

    def evaluate_and_consolidate(self):
        if self.partida.result_str is not None and not self.contabilizado:
            self.pontuacao = self._evaluate()
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
    name = models.CharField(max_length=100, unique=True)
    slug = models.SlugField(unique=True)
    owner = models.ForeignKey(
        Palpiteiro,
        related_name="own_pools",
        on_delete=models.PROTECT,
    )
    teams = models.ManyToManyField(Equipe, related_name="pools")
    guessers = models.ManyToManyField(Palpiteiro, related_name="pools")

    class Meta:
        verbose_name = "bolão"
        verbose_name_plural = "bolões"

    def __str__(self) -> str:
        return self.name

    @admin.display(description="Equipes")
    def number_of_teams(self):
        return self.teams.count()

    @admin.display(description="Palpiteiros")
    def number_of_guessers(self):
        return self.guessers.count()

    @admin.display(description="Rodadas")
    def number_of_rounds(self):
        return self.rounds.count()

    def get_owners(self):
        return self.memberships.filter(is_owner=True)

    def get_admins(self):
        return self.memberships.filter(is_admin=True)
