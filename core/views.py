from datetime import timedelta

from django.views.generic import TemplateView, ListView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect, get_object_or_404
from django.core.exceptions import ObjectDoesNotExist
from django.utils import timezone
from django.urls import reverse
from django.http import QueryDict, HttpResponse

from .models import Rodada, Partida, Palpite, Palpiteiro
from .forms import EnabledPalpiteForm, DisabledPalpiteForm


class IndexView(LoginRequiredMixin, TemplateView):
    template_name = "core/index.html"


@login_required
def palpitar(request):
    """
    TODO: verificar se é vantajoso transformar as transactions dessa
    view em atômicas.

    TODO: refatorar view removendo o exceço de responsabilidades e
    transferindo lógia referente à manipulação dos dados para o escopo
    dos respectivos models.

    TODO: Alterar exibição das partidas encerradas, utilizar parágrafos
    ao invés de formulários.

    TODO: Melhorar obtenção das partidas abertas para palpites.
    Atualmente, somente as partidas da última rodada serão exibidas,
    impossibilitando a criação de novas rodadas enquanto a última não
    tenha sido resolvida.
    """

    try:
        palpiteiro = request.user.palpiteiro
    except:
        return redirect(reverse("core:palpiteiro_nao_encontrado"))
    rodada = Rodada.objects.last()
    partidas_encerradas = rodada.partidas.filter(
        data_hora__lt=timezone.now() - timedelta(minutes=5)
    )
    partidas_abertas = rodada.partidas.filter(
        data_hora__gte=timezone.now() + timedelta(minutes=5)
    )

    if request.method == "POST":
        for partida in partidas_abertas:
            form = EnabledPalpiteForm(request.POST, partida=partida)
            if form.is_valid():
                try:
                    palpite = Palpite.objects.get(
                        palpiteiro=palpiteiro,
                        partida=partida,
                    )
                except ObjectDoesNotExist:
                    palpite = Palpite(
                        palpiteiro=palpiteiro,
                        partida=partida,
                    )
                palpite.gols_mandante = form.cleaned_data[f"gols_mandante"]
                palpite.gols_visitante = form.cleaned_data[f"gols_visitante"]
                palpite.save()
        return redirect(reverse("core:palpitar_sucesso"))

    else:
        form_list = []

        if not partidas_abertas:
            return redirect(reverse("core:palpites_encerrados"))

        for partida in partidas_encerradas:
            try:
                palpite = partida.palpites.get(palpiteiro=palpiteiro)
                dados = {
                    f"gols_mandante_{partida.id}": palpite.gols_mandante,
                    f"gols_visitante_{partida.id}": palpite.gols_visitante,
                }
                form = DisabledPalpiteForm(dados, partida=partida)
            except ObjectDoesNotExist:
                form = DisabledPalpiteForm(partida=partida)
            form_list.append(form)

        for partida in partidas_abertas:
            try:
                palpite = partida.palpites.get(palpiteiro=palpiteiro)
                dados = {
                    f"gols_mandante_{partida.id}": palpite.gols_mandante,
                    f"gols_visitante_{partida.id}": palpite.gols_visitante,
                }
                form = EnabledPalpiteForm(dados, partida=partida)
            except ObjectDoesNotExist:
                form = EnabledPalpiteForm(partida=partida)
            form_list.append(form)

    return render(request, "core/palpitar.html", {"form_list": form_list})


class PalpitarSucessoView(LoginRequiredMixin, TemplateView):
    """
    TODO: bloquear acesso direto a essa view, permitindo apenas acesso
    via redirecionamento a partir da view palpitar
    """

    template_name = "core/palpitar_sucesso.html"


class PalpitesEncerradosView(LoginRequiredMixin, TemplateView):
    """
    TODO: bloquear acesso direto a essa view, permitindo apenas acesso
    via redirecionamento a partir da view palpitar
    """

    template_name = "core/palpites_encerrados.html"


class PalpiteiroNaoEncontradoView(LoginRequiredMixin, TemplateView):
    """
    TODO: bloquear acesso direto a essa view, permitindo apenas acesso
    via redirecionamento a partir da view palpitar
    """

    template_name = "core/palpiteiro_nao_encontrado.html"


class ManualAdminView(LoginRequiredMixin, TemplateView):
    template_name = "core/manual_administracao.html"


class RodadasListView(LoginRequiredMixin, ListView):
    model = Rodada
    template_name = "core/rodadas.html"
    context_object_name = "rodadas"
    ordering = "-id"


@login_required
def detalhes_rodada(request, id_rodada):
    """Busca todas as partidas de uma rodada e os palpites pertencentes
    ao usuário logado para cada uma das partidas. Então, renderiza o
    template core/detalhes_rodada.html com os dados das partidas e seus
    respectivos palpites"""

    palpiteiro_logado = request.user.palpiteiro
    rodada = get_object_or_404(Rodada, pk=id_rodada)
    partidas = rodada.partidas.all()

    dados_palpiteiros = [
        {
            "palpiteiro": palpiteiro,
            "partidas_e_palpites": [],
            "pontuacao": 0,
        }
        for palpiteiro in Palpiteiro.objects.all()
    ]

    for dados_palpiteiro in dados_palpiteiros:
        palpiteiro = dados_palpiteiro["palpiteiro"]

        for partida in partidas:
            try:
                palpite = (
                    partida.palpites.get(palpiteiro=dados_palpiteiro["palpiteiro"])
                    if not partida.aberta_para_palpites()
                    or palpiteiro == palpiteiro_logado
                    else None
                )

                if palpite is not None and partida.resultado is not None:
                    dados_palpiteiro["pontuacao"] += palpite.obter_pontuacao()

            except ObjectDoesNotExist:
                palpite = None

            dados_palpiteiro["partidas_e_palpites"].append(
                {"partida": partida, "palpite": palpite}
            )

    return render(
        request,
        "core/detalhes_rodada.html",
        {"rodada": rodada, "dados_palpiteiros": dados_palpiteiros},
    )


def classificacao(request):
    periodo, inicio, fim = _obter_periodo(request.GET)
    palpiteiros = []
    for palpiteiro in Palpiteiro.objects.all():
        palpiteiros.append(
            {
                "nome": palpiteiro,
                "pontuacao": palpiteiro.obter_pontuacao_no_periodo(inicio, fim),
            },
        )

    palpiteiros.sort(key=lambda p: p["pontuacao"], reverse=True)

    return render(
        request,
        "core/classificacao.html",
        {
            "periodo": periodo,
            "inicio_periodo": inicio.date(),
            "fim_periodo": fim.date(),
            "palpiteiros": palpiteiros,
        },
    )


def _obter_periodo(get_params: QueryDict):
    periodo = get_params.get("periodo") or "mensal"
    inicio_base = timezone.now().replace(day=1, hour=0, minute=0, second=0)
    fim_base = inicio_base.replace(hour=23, minute=59, second=59)

    # todos os meses do ano atual
    if periodo == "anual":
        inicio = inicio_base.replace(month=1)
        fim = fim_base.replace(day=31, month=12)

    # periodo entre data da primeira partida registrada até data atual
    elif periodo == "geral":
        partida = Partida.objects.first()
        if partida is not None:
            inicio = partida.data_hora
        else:
            inicio = timezone.now()
        fim = timezone.now()

    # mes e ano atuais
    else:
        inicio = inicio_base
        fim = (
            fim_base.replace(month=inicio.month + 1)
            if inicio.month < 12
            else fim_base.replace(month=1, year=inicio.year + 1)
        ) - timedelta(days=1)

    return (periodo, inicio, fim)


def one_signal_worker(request):
    return HttpResponse(
        "importScripts('https://cdn.onesignal.com/sdks/OneSignalSDKWorker.js');",
        headers={"Content-Type": "application/javascript; charset=utf-8"},
    )
