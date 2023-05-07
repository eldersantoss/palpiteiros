from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.forms import CheckboxSelectMultiple, modelform_factory
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, render
from django.utils import timezone
from django.utils.text import slugify
from django.views import generic

from core.helpers import redirect_with_msg

from .forms import RankingPeriodForm
from .models import GuessPool
from .viewmixins import GuessPoolMembershipMixin


class IndexView(LoginRequiredMixin, generic.TemplateView):
    template_name = "core/index.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        guesser = self.request.user.palpiteiro
        involved_pools = guesser.get_involved_pools()
        pools_as_guesser = guesser.pools.all()
        for pool in involved_pools:
            pool.is_pending = (
                pool.has_pending_match(self.request.user.palpiteiro)
                if pool in pools_as_guesser
                else False
            )

        context["display_subtitle"] = any([pool.is_pending for pool in involved_pools])
        context["pools"] = involved_pools

        return context


class CreatePoolView(LoginRequiredMixin, generic.CreateView):
    model = GuessPool
    fields = ["name", "private", "competitions", "teams"]
    template_name = "core/create_pool.html"

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
            widgets={
                "competitions": CheckboxSelectMultiple(),
                "teams": CheckboxSelectMultiple(),
            },
        )

    def form_valid(self, form):
        form.instance.owner = self.request.user.palpiteiro
        slug = slugify(form.instance.name)
        if GuessPool.objects.filter(slug=slug).exists():
            form.add_error(
                "name", "Já existe um bolão com esse nome. Por favor, escolha outro."
            )
            return self.form_invalid()
        form.instance.slug = slug
        return super().form_valid(form)


class ManagePoolView(GuessPoolMembershipMixin, LoginRequiredMixin, generic.UpdateView):
    model = GuessPool
    fields = ["name", "private", "competitions", "teams", "guessers"]
    template_name = "core/manage_pool.html"
    slug_url_kwarg = "pool_slug"

    def dispatch(self, request, *args, **kwargs):
        if self.pool.user_is_owner:
            return super().dispatch(request, *args, **kwargs)
        return redirect_with_msg(
            self.request,
            "error",
            "Você não possui autorização pra realizar esta ação ❌",
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

    def get_form(self, form_class=None):
        form = super().get_form(form_class)
        form.fields["guessers"].queryset = self.pool.guessers.all()
        return form

    def get_form_class(self):
        super().get_form_class()
        return modelform_factory(
            self.model,
            fields=self.fields,
            widgets={
                "competitions": CheckboxSelectMultiple(),
                "teams": CheckboxSelectMultiple(),
                "guessers": CheckboxSelectMultiple(),
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
            msg_type = "success"
            msg = f"Bem-vindo(a) ao bolão <strong>{pool}</strong>! Boa sorte 😀🍀🔥"
        else:
            msg_type = "error"
            msg = "Você já é membro do bolão ❌"
        return redirect_with_msg(self.request, msg_type, msg, "mid", pool)


class GuessPoolSignOutView(GuessPoolMembershipMixin, LoginRequiredMixin, generic.View):
    def get(self, request, *args, **kwargs):
        if self.pool.user_is_owner:
            return redirect_with_msg(
                self.request,
                "error",
                "Não é possível sair do bolão porque você é o proprietário 🚫",
                to=self.pool,
            )

        self.pool.remove_guesser(self.guesser)

        return redirect_with_msg(
            self.request,
            "warning",
            f"Você saiu do bolão <strong>{self.pool}</strong> 👋🏃",
        )


class GuessPoolListView(LoginRequiredMixin, generic.ListView):
    queryset = GuessPool.objects.filter(private=False)
    template_name = "core/search_pool.html"
    context_object_name = "pools"

    def get(self, request, *args, **kwargs):
        if not self.get_queryset().exists():
            return redirect_with_msg(
                self.request,
                "error",
                "Nenhum bolão público cadastrado..."
                + " Que tal criar um agora mesmo?"
                + " Basta clicar em <strong>Criar bolão</strong>"
                + " e configurar como quiser 😎",
                "long",
            )
        return super().get(request, *args, **kwargs)


class PoolHomeView(GuessPoolMembershipMixin, LoginRequiredMixin, generic.TemplateView):
    template_name = "core/pool_home.html"


class GuessesView(GuessPoolMembershipMixin, LoginRequiredMixin, generic.View):
    def dispatch(self, request, *args, **kwargs):
        if self.pool.user_is_owner and not self.pool.user_is_guesser:
            return redirect_with_msg(
                self.request,
                "error",
                "Você não está cadastrado como palpiteiro."
                + " Acesse <strong>Gerenciar bolão</strong>"
                + " e marque seu usuário como <strong>Palpiteiro</strong>"
                + " para ter acesso à esta ação.",
                "long",
                self.pool,
            )
        return super().dispatch(request, *args, **kwargs)

    def get(self, *args, **kwargs):
        return self._get_post_handler(*args, **kwargs)

    def post(self, *args, **kwargs):
        return self._get_post_handler(*args, **kwargs)

    def _get_post_handler(self, *args, **kwargs):
        open_matches = self.pool.get_update_or_create_guesses(
            self.guesser,
            self.request.POST,
        )
        if not open_matches.exists():
            return redirect_with_msg(
                self.request,
                "error",
                "Não existem partidas abertas neste momento ❌",
                "short",
                self.pool,
            )
        if self.request.method == "POST":
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


class RankingView(GuessPoolMembershipMixin, LoginRequiredMixin, generic.TemplateView):
    template_name = "core/ranking.html"

    def get(self, *args, **kwargs):
        context = self.get_context_data(**kwargs)
        if not context["ranking"].exists():
            return redirect_with_msg(
                self.request,
                "error",
                "Nenhum palpiteiro cadastrado no bolão 😕",
                "short",
                self.pool,
            )
        return self.render_to_response(context)

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
            return redirect_with_msg(
                self.request,
                "error",
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


def one_signal_worker(request):
    return HttpResponse(
        "importScripts('https://cdn.onesignal.com/sdks/OneSignalSDKWorker.js');",
        headers={"Content-Type": "application/javascript; charset=utf-8"},
    )
