from django.views.generic import TemplateView, ListView, DetailView, View
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.shortcuts import render, redirect
from django.utils import timezone
from django.urls import reverse_lazy
from django.http import HttpResponse

from .models import Palpiteiro
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


class GuessesView(GuessPoolMembershipMixin, LoginRequiredMixin, View):
    def get(self, *args, **kwargs):
        open_matches = self.pool.get_update_or_create_guesses(self.guesser)
        if not open_matches.exists():
            return self.redirect_to_pool_home_with_error_msg(
                "Não existem partidas abertas nesse momento! ❌"
            )
        return render(
            self.request,
            "core/guesses.html",
            {"pool": self.pool, "open_matches": open_matches},
        )

    def post(self, *args, **kwargs):
        open_matches = self.pool.get_update_or_create_guesses(
            self.guesser,
            self.request.POST,
        )
        messages.success(
            self.request,
            "Palpites salvos! ✅",
            "temp-msg short-time-msg",
        )
        return render(
            self.request,
            "core/guesses.html",
            {"pool": self.pool, "open_matches": open_matches},
        )


class RankingView(GuessPoolMembershipMixin, LoginRequiredMixin, TemplateView):
    template_name = "core/ranking.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        form = RankingPeriodForm(self.request.GET)
        if form.is_valid():
            month = int(form.cleaned_data["mes"])
            year = int(form.cleaned_data["ano"])
        else:
            month = timezone.now().month
            year = timezone.now().year
            form = RankingPeriodForm({"mes": month, "ano": year})
        context["period_form"] = form
        context["ranking"] = self.pool.get_ranking(month, year)
        return context


class RoundsListView(GuessPoolMembershipMixin, LoginRequiredMixin, ListView):
    template_name = "core/rodadas.html"
    context_object_name = "rodadas"
    ordering = "-id"

    def get(self, request, *args, **kwargs):
        if not self.get_queryset().exists():
            return self.redirect_to_pool_home_with_error_msg(
                "Nenhuma rodada encontrada 😕",
            )
        return super().get(request, *args, **kwargs)

    def get_queryset(self):
        return self.pool.get_visible_rounds()


class RoundDetailView(GuessPoolMembershipMixin, LoginRequiredMixin, DetailView):
    """Busca todas as partidas de uma rodada e os palpites do usuário
    logado. Então, renderiza o template core/round_details.html com os
    dados das partidas e seus respectivos palpites"""

    context_object_name = "round"
    template_name = "core/round_details.html"
    slug_url_kwarg = "round_slug"

    def get_queryset(self):
        return self.pool.get_rounds()

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["round_details"] = self.object.get_details(
            self.pool,
            self.guesser,
        )
        return context


class ManualAdminView(LoginRequiredMixin, TemplateView):
    template_name = "core/manual_administracao.html"


def one_signal_worker(request):
    return HttpResponse(
        "importScripts('https://cdn.onesignal.com/sdks/OneSignalSDKWorker.js');",
        headers={"Content-Type": "application/javascript; charset=utf-8"},
    )
