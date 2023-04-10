from django.views.generic import TemplateView, ListView, DetailView, View
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.shortcuts import render, redirect
from django.utils import timezone
from django.urls import reverse_lazy
from django.http import HttpResponse

from .models import Rodada, Palpiteiro, Partida
from .forms import RankingPeriodForm
from .viewmixins import GuessPoolMembershipMixin


class IndexView(LoginRequiredMixin, TemplateView):
    template_name = "core/index.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["pools"] = self.request.user.palpiteiro.pools.all()
        return context


class PoolHome(GuessPoolMembershipMixin, LoginRequiredMixin, TemplateView):
    template_name = "core/pool_home.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["pool"] = self.get_pool()
        return context


@login_required
def guesses(request):
    try:
        guesser = request.user.palpiteiro
    except Palpiteiro.DoesNotExist:
        messages.error(
            request,
            "Nenhum palpiteiro cadastrado! ❌",
            "temp-msg short-time-msg",
        )
        return redirect(
            reverse_lazy(
                "core:pool_home",
                kwargs={"pool_slug": pool.slug},
            )
        )

    if not Rodada.objects.exists():
        messages.error(
            request,
            "Nenhuma rodada cadastrada! ❌",
            "temp-msg short-time-msg",
        )
        return redirect(
            reverse_lazy(
                "core:pool_home",
                kwargs={"pool_slug": pool.slug},
            )
        )

    if not Partida.have_open_matches_for_any_active_round():
        messages.error(
            request,
            "Rodada encerrada! ❌",
            "temp-msg short-time-msg",
        )
        return redirect(
            reverse_lazy(
                "core:pool_home",
                kwargs={"pool_slug": pool.slug},
            )
        )

    context = {
        "closed_matches": Partida.get_closed_matches_with_guesses(guesser),
        "open_matches": Partida.create_update_or_retrieve_guesses_from_your_forms(
            guesser, request.POST
        ),
    }

    if request.method == "POST":
        messages.success(
            request,
            "Palpites salvos! ✅",
            "temp-msg short-time-msg",
        )

    return render(request, "core/guesses.html", context)


class GuessesView(GuessPoolMembershipMixin, LoginRequiredMixin, View):
    def get(self, request, *args, **kwargs):
        pool = self.get_pool()

        try:
            guesser = request.user.palpiteiro
        except Palpiteiro.DoesNotExist:
            messages.error(
                request,
                "Nenhum palpiteiro cadastrado! ❌",
                "temp-msg short-time-msg",
            )
            return redirect(
                reverse_lazy(
                    "core:pool_home",
                    kwargs={"pool_slug": pool.slug},
                )
            )

        open_matches = pool.get_open_matches_with_guesses_forms(guesser)
        if not open_matches.exists():
            messages.error(
                request,
                "Não existem partidas abertas nesse momento! ❌",
                "temp-msg short-time-msg",
            )
            return redirect(
                reverse_lazy(
                    "core:pool_home",
                    kwargs={"pool_slug": pool.slug},
                )
            )

        return render(
            self.request,
            "core/guesses.html",
            {"pool": pool, "open_matches": open_matches},
        )

    def post(self, request, *args, **kwargs):
        pool = self.get_pool()
        guesser = self.request.user.palpiteiro
        messages.success(
            request,
            "Palpites salvos! ✅",
            "temp-msg short-time-msg",
        )
        return render(
            self.request,
            "core/guesses.html",
            {
                "pool": pool,
                "open_matches": pool.get_open_matches_with_guesses_forms(
                    guesser, self.request.POST
                ),
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
    if not ranking:
        messages.error(
            request,
            "Não existem palpiteiros cadastrados no bolão 😕",
            "temp-msg",
        )
        return redirect(
            reverse_lazy(
                "core:pool_home",
                kwargs={"pool_slug": pool.slug},
            )
        )
    return render(
        request,
        "core/ranking.html",
        {"period_form": form, "ranking": ranking},
    )


class RoundsListView(GuessPoolMembershipMixin, LoginRequiredMixin, ListView):
    template_name = "core/rodadas.html"
    context_object_name = "rodadas"
    ordering = "-id"

    def get(self, request, *args, **kwargs):
        if not self.get_queryset().exists():
            messages.error(
                request,
                "Nenhuma rodada encontrada 😕",
                "temp-msg short-time-msg",
            )
            return redirect(
                reverse_lazy(
                    "core:pool_home",
                    kwargs={"pool_slug": pool.slug},
                )
            )
        return super().get(request, *args, **kwargs)

    def get_queryset(self):
        return self.get_pool().get_visible_rounds()

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["pool"] = self.get_pool()
        return context


class RoundDetailView(GuessPoolMembershipMixin, LoginRequiredMixin, DetailView):
    """Busca todas as partidas de uma rodada e os palpites do usuário
    logado. Então, renderiza o template core/round_details.html com os
    dados das partidas e seus respectivos palpites"""

    context_object_name = "round"
    template_name = "core/round_details.html"
    slug_url_kwarg = "round_slug"

    def get_queryset(self):
        return self.get_pool().get_rounds()

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["round_details"] = self.object.get_details(self.request.user)
        return context


class ManualAdminView(LoginRequiredMixin, TemplateView):
    template_name = "core/manual_administracao.html"


def one_signal_worker(request):
    return HttpResponse(
        "importScripts('https://cdn.onesignal.com/sdks/OneSignalSDKWorker.js');",
        headers={"Content-Type": "application/javascript; charset=utf-8"},
    )
