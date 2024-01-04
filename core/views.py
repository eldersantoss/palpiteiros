from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.forms import CheckboxSelectMultiple, modelform_factory
from django.shortcuts import get_object_or_404, render
from django.utils import timezone
from django.utils.text import slugify
from django.views import generic

from core.helpers import redirect_with_msg

from .forms import GuesserEditForm, GuessForm, RankingPeriodForm, UserEditForm
from .models import Guess, GuessPool
from .viewmixins import GuessPoolMembershipMixin


class IndexView(LoginRequiredMixin, generic.TemplateView):
    template_name = "core/index.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        guesser = self.request.user.guesser
        involved_pools = guesser.get_involved_pools()
        pools_as_guesser = guesser.pools.all()
        for pool in involved_pools:
            pool.is_pending = (
                pool.has_pending_match(self.request.user.guesser)
                if pool in pools_as_guesser
                else False
            )

        context["display_subtitle"] = any(
            [pool.is_pending for pool in involved_pools]
        )
        context["pools"] = involved_pools

        return context


class ProfileView(LoginRequiredMixin, generic.View):
    template_name = "core/profile.html"

    def get(self, *args, **kwargs):
        user_edit_form = UserEditForm(instance=self.request.user)
        guesser_edit_form = GuesserEditForm(instance=self.request.user.guesser)

        return render(
            self.request,
            self.template_name,
            {
                "user_edit_form": user_edit_form,
                "guesser_edit_form": guesser_edit_form,
            },
        )

    def post(self, *args, **kwargs):
        user_edit_form = UserEditForm(
            instance=self.request.user,
            data=self.request.POST,
        )
        guesser_edit_form = GuesserEditForm(
            instance=self.request.user.guesser,
            data=self.request.POST,
        )

        if user_edit_form.is_valid() and guesser_edit_form.is_valid():
            user_edit_form.save()
            guesser_edit_form.save()

            messages.success(
                self.request,
                "Perfil atualizado ✅",
                "temp-msg short-time-msg",
            )

        else:
            messages.error(
                self.request,
                "Corrija os erros abaixo ❌",
                "temp-msg short-time-msg",
            )

        return render(
            self.request,
            self.template_name,
            {
                "user_edit_form": user_edit_form,
                "guesser_edit_form": guesser_edit_form,
            },
        )


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
        form.instance.owner = self.request.user.guesser
        slug = slugify(form.instance.name)
        if GuessPool.objects.filter(slug=slug).exists():
            form.add_error(
                "name",
                "Já existe um bolão com esse nome. Por favor, escolha outro.",
            )
            return self.form_invalid()
        form.instance.slug = slug
        return super().form_valid(form)


class ManagePoolView(
    GuessPoolMembershipMixin, LoginRequiredMixin, generic.UpdateView
):
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
        form.instance.owner = self.request.user.guesser
        form.instance.slug = slugify(form.instance.name)
        return super().form_valid(form)


class GuessPoolSignInView(LoginRequiredMixin, generic.View):
    def get(self, *args, **kwargs):
        uuid = kwargs.get("uuid")
        pool = get_object_or_404(GuessPool, uuid=uuid)
        guesser = self.request.user.guesser
        if not pool.guesser_is_member(guesser):
            pool.signin_new_guesser(guesser)
            msg_type = "success"
            msg = (
                f"Bem-vindo(a) ao bolão <strong>{pool}</strong>! Boa sorte 😀🍀🔥"
            )
        else:
            msg_type = "error"
            msg = "Você já é membro do bolão ❌"
        return redirect_with_msg(self.request, msg_type, msg, "mid", pool)


class GuessPoolSignOutView(
    GuessPoolMembershipMixin, LoginRequiredMixin, generic.View
):
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


class PoolHomeView(
    GuessPoolMembershipMixin, LoginRequiredMixin, generic.TemplateView
):
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
        open_matches = self.pool.get_open_matches()

        if not open_matches.exists():
            return redirect_with_msg(
                self.request,
                "error",
                "Não existem partidas abertas neste momento ❌",
                "short",
                self.pool,
            )

        guess_forms = []
        for match in open_matches:
            try:
                guess = self.pool.guesses.get(
                    match=match,
                    guesser=self.guesser,
                )
                initial_data = {
                    f"home_goals_{match.id}": guess.home_goals,
                    f"away_goals_{match.id}": guess.away_goals,
                }

            except Guess.DoesNotExist:
                initial_data = None

            guess_forms.append(GuessForm(initial_data, match=match))

        return render(
            self.request,
            "core/guesses.html",
            {"pool": self.pool, "guess_forms": guess_forms},
        )

    def post(self, *args, **kwargs):
        for_all_pools = bool(self.request.POST.get("for_all_pools"))

        open_matches = self.pool.get_open_matches()

        if not open_matches.exists():
            return redirect_with_msg(
                self.request,
                "error",
                "Não existem partidas abertas neste momento ❌",
                "short",
                self.pool,
            )

        guess_forms = []
        for match in open_matches:
            guess_form = GuessForm(self.request.POST, match=match)

            if guess_form.is_valid():
                """
                Quando o palpite é aproveitado em todos os bolões, a mesma
                instância de palpite é adicionada no relacionamento guesses
                de todos os bolões nos quais ele é aproveitado. Então, quando
                essa instância for modificada, todos os bolões terão seus
                palpites afetados. Por isso, só se deve ATUALIZAR um palpite
                se ele for aproveitado em todos os bolões (for_all_pools). Caso
                contrário, quando o palpite for exclusivo de um único bolão,
                deve-se sempre criar um novo palpite e substituir o antigo pelo
                novo na relação guesses.
                """

                guess = Guess.objects.create(
                    match=match,
                    guesser=self.guesser,
                    home_goals=guess_form.cleaned_data["home_goals"],
                    away_goals=guess_form.cleaned_data["away_goals"],
                )
                self.pool.add_guess_to_pools(guess, for_all_pools)
                self.pool.delete_orphans_guesses()

                guess_forms.append(guess_form)

            else:
                try:
                    guess = self.pool.guesses.get(
                        match=match,
                        guesser=self.guesser,
                    )
                    initial_data = {
                        f"home_goals_{match.id}": guess.home_goals,
                        f"away_goals_{match.id}": guess.away_goals,
                    }

                except Guess.DoesNotExist:
                    initial_data = None

                guess_forms.append(GuessForm(initial_data, match=match))

        messages.success(
            self.request,
            "Palpites salvos ✅",
            "temp-msg short-time-msg",
        )

        return render(
            self.request,
            "core/guesses.html",
            {"pool": self.pool, "guess_forms": guess_forms},
        )


class RankingView(
    GuessPoolMembershipMixin, LoginRequiredMixin, generic.TemplateView
):
    template_name = "core/ranking.html"

    def get(self, *args, **kwargs):
        context = self.get_context_data(**kwargs)
        if not context["guessers"].exists():
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

        current_period = {
            "mes": timezone.now().month,
            "ano": timezone.now().year,
            "rodada": timezone.now().isocalendar().week,
        }
        form = RankingPeriodForm(self.request.GET or current_period)
        form.is_valid()

        month = int(form.cleaned_data["mes"])
        year = int(form.cleaned_data["ano"])
        round_ = int(form.cleaned_data["rodada"])

        context["period_form"] = form
        context["guessers"] = self.pool.get_guessers_with_score_and_guesses(
            month, year, round_
        )

        return context
