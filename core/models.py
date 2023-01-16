from datetime import timedelta, datetime

from django.db import models
from django.conf import settings
from django.contrib import admin
from django.utils import timezone


class Equipe(models.Model):
    nome = models.CharField(max_length=50)
    abreviacao = models.CharField(max_length=3, default="???")

    def __str__(self) -> str:
        return self.nome


class Rodada(models.Model):
    def _gerar_label_default():
        meses = [
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
        mes = timezone.now().month
        ano = timezone.now().year
        try:
            numero_rodada = (
                Rodada.objects.last().partidas.filter(data_hora__month=mes).count() + 1
            )
        except AttributeError:
            numero_rodada = 1

        return f"#{str(numero_rodada).zfill(2)} de {meses[mes - 1]} de {ano}"

    label = models.CharField(max_length=50, default=_gerar_label_default)

    @admin.display(description="Número de partidas")
    def numero_partidas(self) -> int:
        return self.partidas.count()

    @admin.display(
        boolean=True,
        description="Aberta para palpites?",
    )
    def aberta_para_palpites(self) -> bool:
        partidas = self.partidas.all()
        horario_limite = timezone.now() - timedelta(minutes=15)
        return any([partida.data_hora > horario_limite for partida in partidas])

    @property
    def abertura(self):
        return self.partidas.order_by("data_hora").first().data_hora

    @property
    def fechamento(self):
        return self.partidas.order_by("data_hora").last().data_hora

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
        return self.data_hora > timezone.now()


class Palpiteiro(models.Model):
    usuario = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)

    def obter_pontuacao_geral(self):
        palpites = self.palpites.all()
        pontuacao = self.calcular_pontuacao(palpites)
        return pontuacao

    def obter_pontuacao_no_periodo(self, inicio: datetime, fim: datetime):
        palpites = self.obter_palpites_no_periodo(inicio, fim)
        pontuacao = self.calcular_pontuacao(palpites)
        return pontuacao

    def obter_palpites_no_periodo(
        self,
        inicio: datetime,
        fim: datetime,
    ) -> models.QuerySet:
        return self.palpites.filter(
            partida__data_hora__gte=inicio,
            partida__data_hora__lte=fim,
        )

    def calcular_pontuacao(self, palpites: models.QuerySet["Palpite"]):
        pontuacao = sum([palpite.obter_pontuacao() for palpite in palpites])
        return pontuacao

    def __str__(self) -> str:
        return f"{self.usuario.first_name}"


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
    gols_mandante = models.PositiveIntegerField(blank=True, null=True)
    gols_visitante = models.PositiveIntegerField(blank=True, null=True)
    pontuacao = models.PositiveIntegerField(default=0)
    contabilizado = models.BooleanField(default=False)

    def __str__(self) -> str:
        return (
            f"{self.partida.mandante.nome} {self.gols_mandante}"
            + " x "
            + f"{self.gols_visitante} {self.partida.visitante.nome}"
        )

    @property
    def resultado(self) -> str:
        return f"{self.gols_mandante} x {self.gols_visitante}"

    def obter_pontuacao(self) -> int:
        if not self.contabilizado:
            self._avaliar_pontuacao_e_contabilizar_palpite()
        return self.pontuacao

    def _avaliar_pontuacao_e_contabilizar_palpite(self):

        if self.partida.resultado is None:
            return

        ACERTOU_RESULTADO_CRAVADO = (
            self.gols_mandante == self.partida.gols_mandante
            and self.gols_visitante == self.partida.gols_visitante
        )

        ACERTOU_VENCEDOR = (
            self.gols_mandante > self.gols_visitante
            and self.partida.gols_mandante > self.partida.gols_visitante
        ) or (
            self.gols_mandante < self.gols_visitante
            and self.partida.gols_mandante < self.partida.gols_visitante
        )

        ACERTOU_GOLS_MANDANTE_OU_VISITANTE = (
            self.gols_mandante > 0 and self.partida.gols_mandante > 0
        ) or (self.gols_visitante > 0 and self.partida.gols_visitante > 0)

        ACERTOU_GOLS_MANDANTE_E_VISITANTE = (
            self.gols_mandante > 0 and self.partida.gols_mandante > 0
        ) and (self.gols_visitante > 0 and self.partida.gols_visitante > 0)

        PONTUACAO_RESULTADO_CRAVADO = 10
        PONTUACAO_VENCEDOR = 5
        PONTUACAO_GOLS_MANDANTE_E_VISITANTE = 2
        PONTUACOES_GOLS_MANDANTE_OU_VISITANTE = 1

        if ACERTOU_RESULTADO_CRAVADO:
            self.pontuacao = PONTUACAO_RESULTADO_CRAVADO
        else:
            if ACERTOU_VENCEDOR:
                self.pontuacao = PONTUACAO_VENCEDOR
            elif ACERTOU_GOLS_MANDANTE_E_VISITANTE:
                self.pontuacao = PONTUACAO_GOLS_MANDANTE_E_VISITANTE
            elif ACERTOU_GOLS_MANDANTE_OU_VISITANTE:
                self.pontuacao = PONTUACOES_GOLS_MANDANTE_OU_VISITANTE
            else:
                self.pontuacao = 0

        self.contabilizado = True
        self.save()
