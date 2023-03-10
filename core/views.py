from datetime import timedelta

from django.views.generic import TemplateView, ListView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect, get_object_or_404
from django.utils import timezone
from django.urls import reverse
from django.http import QueryDict, HttpResponse

from .models import Rodada, Partida, Palpite, Palpiteiro
from .forms import EnabledPalpiteForm, RankingPeriodForm


class IndexView(LoginRequiredMixin, TemplateView):
    template_name = "core/index.html"


@login_required
def palpitar(request):
    try:
        palpiteiro = request.user.palpiteiro
    except Palpiteiro.DoesNotExist:
        return redirect(reverse("core:palpiteiro_nao_encontrado"))

    if not Rodada.objects.exists():
        return redirect(reverse("core:rodada_nao_encontrada"))

    rodada_mais_recente = Rodada.objects.first()
    partidas_encerradas = rodada_mais_recente.partidas_encerradas()
    partidas_abertas = rodada_mais_recente.partidas_abertas()

    if request.method == "POST":
        for partida in partidas_abertas:
            form = EnabledPalpiteForm(request.POST, partida=partida)
            form.is_valid()
            try:
                palpite = partida.palpites.get(palpiteiro=palpiteiro)
                palpite.gols_mandante = form.cleaned_data[f"gols_mandante"]
                palpite.gols_visitante = form.cleaned_data[f"gols_visitante"]
            except Palpite.DoesNotExist:
                palpite = partida.palpites.create(
                    palpiteiro=palpiteiro,
                    gols_mandante=form.cleaned_data[f"gols_mandante"],
                    gols_visitante=form.cleaned_data[f"gols_visitante"],
                )
            palpite.save()
        return redirect(reverse("core:palpitar_sucesso"))

    else:
        if not partidas_abertas:
            return redirect(reverse("core:palpites_encerrados"))

        dados_palpites_encerrados = []
        for partida in partidas_encerradas:
            try:
                palpite = partida.palpites.get(palpiteiro=palpiteiro)
            except Palpite.DoesNotExist:
                palpite = None
            dados_palpites_encerrados.append(
                {"partida": partida, "palpite": palpite},
            )

        forms_palpites_abertos = []
        for partida in partidas_abertas:
            try:
                palpite = partida.palpites.get(palpiteiro=palpiteiro)
            except Palpite.DoesNotExist:
                dados_palpite = None
            else:
                dados_palpite = {
                    f"gols_mandante_{partida.id}": palpite.gols_mandante,
                    f"gols_visitante_{partida.id}": palpite.gols_visitante,
                }
            forms_palpites_abertos.append(
                EnabledPalpiteForm(dados_palpite, partida=partida),
            )

    return render(
        request,
        "core/palpitar.html",
        {
            "dados_palpites_encerrados": dados_palpites_encerrados,
            "forms_palpites_abertos": forms_palpites_abertos,
        },
    )


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


class RodadaNaoEncontradaView(LoginRequiredMixin, TemplateView):
    """
    TODO: bloquear acesso direto a essa view, permitindo apenas acesso
    via redirecionamento a partir da view palpitar
    """

    template_name = "core/rodada_nao_encontrada.html"


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
    ao usu??rio logado para cada uma das partidas. Ent??o, renderiza o
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
                    dados_palpiteiro["pontuacao"] += palpite.obter_pontuacao() or 0

            except Palpite.DoesNotExist:
                palpite = None

            dados_palpiteiro["partidas_e_palpites"].append(
                {"partida": partida, "palpite": palpite}
            )

    return render(
        request,
        "core/detalhes_rodada.html",
        {"rodada": rodada, "dados_palpiteiros": dados_palpiteiros},
    )


@login_required
def classificacao(request):
    current_period = {"mes": timezone.now().month, "ano": timezone.now().year}
    form = RankingPeriodForm(request.GET or current_period)
    if form.is_valid():
        month = int(form.cleaned_data["mes"])
        year = int(form.cleaned_data["ano"])
    else:
        month = current_period["mes"]
        year = current_period["ano"]
    form = RankingPeriodForm({"mes": month, "ano": year})
    ranking = Palpiteiro.get_ranking(month, year)
    return render(
        request,
        "core/classificacao.html",
        {"period_form": form, "ranking": ranking},
    )


def one_signal_worker(request):
    return HttpResponse(
        "importScripts('https://cdn.onesignal.com/sdks/OneSignalSDKWorker.js');",
        headers={"Content-Type": "application/javascript; charset=utf-8"},
    )
