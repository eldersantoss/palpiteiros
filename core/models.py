from datetime import timedelta, datetime

from django.db import models
from django.conf import settings
from django.contrib import admin
from django.utils import timezone


class Equipe(models.Model):
    nome = models.CharField(max_length=50)
    abreviacao = models.CharField(max_length=3, default="???")

    class Meta:
        ordering = ("nome",)

    def __str__(self) -> str:
        return self.nome


class Rodada(models.Model):
    def _gerar_label_default():
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

        try:
            ultima_partida = Partida.objects.order_by("data_hora").last()
            numero_ultima_rodada = int(ultima_partida.rodada.label.split(" ")[0][:-1])
            numero_rodada = (
                numero_ultima_rodada + 1
                if mes_atual == ultima_partida.data_hora.month
                else 1
            )

        except AttributeError:
            numero_rodada = 1

        return f"{numero_rodada}ª rodada de {nome_meses[mes_atual - 1]} de {ano_atual}"

    label = models.CharField(
        max_length=50,
        default=_gerar_label_default,
    )

    class Meta:
        ordering = ("-id",)

    @admin.display(description="Número de partidas")
    def numero_partidas(self) -> int:
        return self.partidas.count()

    @admin.display(boolean=True, description="Aberta para palpites?")
    def aberta_para_palpites(self):
        return any([partida.aberta_para_palpites() for partida in self.partidas.all()])

    @property
    def abertura(self):
        try:
            return self.partidas.order_by("data_hora").first().data_hora
        except AttributeError:
            return timezone.now()

    @property
    def fechamento(self):
        try:
            return self.partidas.order_by("data_hora").last().data_hora
        except AttributeError:
            return timezone.now()

    def partidas_abertas(self):
        data_hora_encerramento = timezone.now() + timedelta(minutes=30)
        return self.partidas.filter(data_hora__gt=data_hora_encerramento)

    def partidas_encerradas(self):
        data_hora_encerramento = timezone.now() + timedelta(minutes=30)
        return self.partidas.filter(data_hora__lte=data_hora_encerramento)

    def __str__(self) -> str:
        return self.label


class Partida(models.Model):
    rodada = models.ForeignKey(
        Rodada,
        on_delete=models.CASCADE,
        related_name="partidas",
    )
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
        ordering = ("data_hora",)

    def __str__(self):
        return f"{self.mandante.nome} x {self.visitante.nome}"

    @property
    def abreviacao(self):
        return (
            f"{self.mandante.abreviacao.upper()} x {self.visitante.abreviacao.upper()}"
        )

    @property
    def resultado(self):
        return (
            f"{self.gols_mandante} x {self.gols_visitante}"
            if self.gols_mandante is not None and self.gols_visitante is not None
            else None
        )

    @admin.display(
        boolean=True,
        description="Aberta para palpites?",
    )
    def aberta_para_palpites(self):
        return timezone.now() + timedelta(minutes=30) < self.data_hora


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

        print(f"Start period: {start}")
        print(f"End period: {end}")
        print(f"Problmatic math: {Partida.objects.get(id=94).data_hora}")

        guessers = list(cls.objects.all())
        for guesser in guessers:
            guesser.score = guesser.obter_pontuacao_no_periodo(start, end)
        guessers.sort(key=lambda p: p.score, reverse=True)
        return guessers

    @admin.display(description="Pontuação geral")
    def obter_pontuacao_geral(self):
        palpites = self.palpites.all()
        pontuacao = self.calcular_pontuacao(palpites)
        return pontuacao

    def obter_pontuacao_no_periodo(self, inicio: datetime, fim: datetime):
        palpites = self.palpites.filter(
            partida__data_hora__gt=inicio + timedelta(hours=3),
            partida__data_hora__lt=fim + timedelta(hours=3),
        )
        pontuacao = self.calcular_pontuacao(palpites)
        return pontuacao

    def calcular_pontuacao(self, palpites: models.QuerySet["Palpite"]):
        pontuacao = sum([palpite.obter_pontuacao() or 0 for palpite in palpites])
        return pontuacao

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
    pontuacao = models.PositiveIntegerField(blank=True, null=True)
    contabilizado = models.BooleanField(default=False)

    def __str__(self) -> str:
        return (
            f"{self.partida.mandante.nome} {self.gols_mandante}"
            + " x "
            + f"{self.gols_visitante} {self.partida.visitante.nome}"
        )

    @property
    def aberto(self):
        return timezone.now() - timedelta(minutes=30) > self.partida.data_hora

    @property
    def resultado(self) -> str:
        return f"{self.gols_mandante} x {self.gols_visitante}"

    def obter_pontuacao(self) -> int | None:
        if not self.contabilizado:
            self._avaliar_pontuacao_e_contabilizar_palpite()
        return self.pontuacao

    def _avaliar_pontuacao_e_contabilizar_palpite(self):
        if self.partida.resultado is None:
            return

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
            self.pontuacao = PONTUACAO_ACERTO_CRAVADO
        elif ACERTO_PARCIAL_COM_GOLS:
            self.pontuacao = PONTUACAO_ACERTO_PARCIAL_COM_GOLS
        elif ACERTO_EMPATE:
            self.pontuacao = PONTUACAO_ACERTO_EMPATE
        elif ACERTO_PARCIAL:
            self.pontuacao = PONTUACAO_ACERTO_PARCIAL
        elif ACERTO_SOMENTE_GOLS:
            self.pontuacao = PONTUACAO_ACERTO_SOMENTE_GOLS
        else:
            self.pontuacao = 0

        if self.partida.pontuacao_dobrada:
            self.pontuacao *= 2

        self.contabilizado = True
        self.save()
