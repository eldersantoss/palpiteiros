from django.views.generic import TemplateView, ListView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.shortcuts import render, redirect, get_object_or_404
from django.utils import timezone
from django.urls import reverse
from django.http import HttpResponse

from .models import Rodada, Palpite, Palpiteiro, Partida
from .forms import GuessForm, RankingPeriodForm


class IndexView(LoginRequiredMixin, TemplateView):
    template_name = "core/index.html"


@login_required
def guesses(request):
    try:
        guesser = request.user.palpiteiro
    except Palpiteiro.DoesNotExist:
        messages.error(request, "Nenhum palpiteiro cadastrado! ❌", "temp-msg")
        return redirect(reverse("core:index"))

    if not Rodada.objects.exists():
        messages.error(request, "Nenhuma rodada cadastrada! ❌", "temp-msg")
        return redirect(reverse("core:index"))

    if not Partida.have_open_matches_for_any_active_round():
        messages.error(request, "Rodada encerrada! ❌", "temp-msg")
        return redirect(reverse("core:index"))

    context = {
        "closed_matches": Partida.get_closed_matches_with_guesses(guesser),
        "open_matches": Partida.create_update_or_retrieve_guesses_from_your_forms(
            guesser, request.POST
        ),
    }

    if request.method == "POST":
        messages.success(request, "Palpites salvos! ✅", "temp-msg")

    return render(request, "core/guesses.html", context)


class ManualAdminView(LoginRequiredMixin, TemplateView):
    template_name = "core/manual_administracao.html"


class RodadasListView(LoginRequiredMixin, ListView):
    model = Rodada
    template_name = "core/rodadas.html"
    context_object_name = "rodadas"
    ordering = "-id"


@login_required
def round_details(request, id_rodada):
    """Busca todas as partidas de uma rodada e os palpites pertencentes
    ao usuário logado para cada uma das partidas. Então, renderiza o
    template core/round_details.html com os dados das partidas e seus
    respectivos palpites"""

    round_ = get_object_or_404(Rodada, pk=id_rodada)
    return render(
        request,
        "core/round_details.html",
        {
            "round": round_,
            "round_details": round_.get_details(request.user),
        },
    )


@login_required
def ranking(request):
    form = RankingPeriodForm(request.GET)
    if form.is_valid():
        month = int(form.cleaned_data["mes"])
        year = int(form.cleaned_data["ano"])
    else:
        month = timezone.now().month
        year = timezone.now().year
    form = RankingPeriodForm({"mes": month, "ano": year})
    ranking = Palpiteiro.get_ranking(month, year)
    return render(
        request,
        "core/ranking.html",
        {"period_form": form, "ranking": ranking},
    )


def one_signal_worker(request):
    return HttpResponse(
        "importScripts('https://cdn.onesignal.com/sdks/OneSignalSDKWorker.js');",
        headers={"Content-Type": "application/javascript; charset=utf-8"},
    )
