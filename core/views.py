from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.forms import CheckboxSelectMultiple, modelform_factory
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse_lazy
from django.utils import timezone
from django.utils.text import slugify
from django.views import generic

from .forms import RankingPeriodForm
from .models import GuessPool
from .viewmixins import GuessPoolMembershipMixin


class IndexView(LoginRequiredMixin, generic.TemplateView):
    template_name = "core/index.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        pools_as_owner = self.request.user.palpiteiro.own_pools.all()
        pools_as_guesser = self.request.user.palpiteiro.pools.all()
        context["pools"] = pools_as_owner.union(pools_as_guesser).order_by("name")
        return context


class PoolCreateView(LoginRequiredMixin, generic.CreateView):
    model = GuessPool
    fields = ["name", "teams"]
    template_name = "core/create_pool.html"

    def dispatch(self, request, *args, **kwargs):
        if self.request.user.palpiteiro.own_pools.count() >= 2:
            messages.error(
                self.request,
                f"Limite de bolões atingido. Você pode possuir até 2 bolões ❌",
                "temp-msg mid-time-msg",
            )
            return redirect(reverse_lazy("core:index"))
        return super().dispatch(request, *args, **kwargs)

    def post(self, request, *args, **kwargs):
        response = super().post(request, *args, **kwargs)
        if response.status_code == 302:
            messages.success(
                self.request,
                "Tudo pronto ⚽🍀📊😎",
                "temp-msg short-time-msg",
            )
        return response

    def get_form_class(self):
        super().get_form_class()
        return modelform_factory(
            self.model,
            fields=self.fields,
            widgets={"teams": CheckboxSelectMultiple},
        )

    def form_valid(self, form):
        form.instance.owner = self.request.user.palpiteiro
        form.instance.slug = slugify(form.instance.name)
        return super().form_valid(form)


class ManagePoolView(GuessPoolMembershipMixin, LoginRequiredMixin, generic.UpdateView):
    model = GuessPool
    fields = ["name", "teams", "guessers"]
    template_name = "core/manage_pool.html"
    slug_url_kwarg = "pool_slug"

    def dispatch(self, request, *args, **kwargs):
        if self.pool.user_is_owner:
            return super().dispatch(request, *args, **kwargs)
        return self.redirect_to_pool_home_with_error_msg(
            "Você não possui autorização pra realizar esta ação ❌",
            "mid-time-msg",
        )

    def post(self, request, *args, **kwargs):
        response = super().post(request, *args, **kwargs)
        if response.status_code == 302:
            messages.success(
                self.request,
                "Bolão atualizado ✅",
                "temp-msg short-time-msg",
            )
        return response

    def get_form_class(self):
        super().get_form_class()
        return modelform_factory(
            self.model,
            fields=self.fields,
            widgets={
                "teams": CheckboxSelectMultiple,
                "guessers": CheckboxSelectMultiple,
            },
        )

    def form_valid(self, form):
        form.instance.owner = self.request.user.palpiteiro
        form.instance.slug = slugify(form.instance.name)
        return super().form_valid(form)


class GuessPoolSignInView(LoginRequiredMixin, generic.View):
    def get(self, *args, **kwargs):
        uuid = kwargs.get("uuid")
        pool = get_object_or_404(GuessPool, uuid=uuid)
        guesser = self.request.user.palpiteiro
        if not pool.guesser_is_member(guesser):
            pool.signin_new_guesser(guesser)
            messages.success(
                self.request,
                f"Bem-vindo(a) ao bolão 😀",
                "temp-msg short-time-msg",
            )
        else:
            messages.error(
                self.request,
                f"Você já é membro do bolão ❌",
                "temp-msg short-time-msg",
            )
        return redirect(pool)


class PoolHomeView(GuessPoolMembershipMixin, LoginRequiredMixin, generic.TemplateView):
    template_name = "core/pool_home.html"


class GuessesView(GuessPoolMembershipMixin, LoginRequiredMixin, generic.View):
    def get(self, *args, **kwargs):
        open_matches = self.pool.get_update_or_create_guesses(
            self.guesser,
            self.request.POST,
        )
        if not open_matches.exists():
            return self.redirect_to_pool_home_with_error_msg(
                "Não existem partidas abertas nesse momento ❌"
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

    def dispatch(self, request, *args, **kwargs):
        if self.pool.user_is_guesser:
            return super().dispatch(request, *args, **kwargs)
        return self.redirect_to_pool_home_with_error_msg(
            "Você não está cadastrado como palpiteiro."
            + " Acesse <strong>Gerenciar bolão</strong>"
            + " e marque seu usuário como <strong>Palpiteiro</strong>"
            + " para ter acesso à esta ação.",
            "mid-time-msg",
        )


class RankingView(GuessPoolMembershipMixin, LoginRequiredMixin, generic.TemplateView):
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


class RoundsListView(GuessPoolMembershipMixin, LoginRequiredMixin, generic.ListView):
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


class RoundDetailView(GuessPoolMembershipMixin, LoginRequiredMixin, generic.DetailView):
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


class ManualAdminView(LoginRequiredMixin, generic.TemplateView):
    template_name = "core/manual_administracao.html"


def one_signal_worker(request):
    return HttpResponse(
        "importScripts('https://cdn.onesignal.com/sdks/OneSignalSDKWorker.js');",
        headers={"Content-Type": "application/javascript; charset=utf-8"},
    )
