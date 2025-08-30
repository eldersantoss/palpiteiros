import logging

from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.paginator import Paginator
from django.db.models import Q, Sum
from django.forms import CheckboxSelectMultiple, modelform_factory
from django.shortcuts import get_object_or_404, render
from django.utils import timezone
from django.utils.text import slugify
from django.views import generic

from core.helpers import redirect_with_msg

from .forms import (
    GuesserEditForm,
    GuessesPeriodForm,
    GuessForm,
    RankingPeriodForm,
    UserEditForm,
)
from .models import Guess, GuessPool
from .viewmixins import GuessPoolMembershipMixin

logger = logging.getLogger(__name__)


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

        context["display_subtitle"] = any([pool.is_pending for pool in involved_pools])
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
    fields = [
        "name",
        "minutes_before_start_match",
        "hours_before_open_to_guesses",
        "private",
        "competitions",
        "teams",
    ]
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


class ManagePoolView(LoginRequiredMixin, GuessPoolMembershipMixin, generic.UpdateView):
    model = GuessPool
    fields = [
        "name",
        "minutes_before_start_match",
        "hours_before_open_to_guesses",
        "private",
        "competitions",
        "teams",
        "guessers",
    ]
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
            msg = f"Bem-vindo(a) ao bolão <strong>{pool}</strong>! Boa sorte 😀🍀🔥"
        else:
            msg_type = "error"
            msg = "Você já é membro do bolão ❌"
        return redirect_with_msg(self.request, msg_type, msg, "mid", pool)


class GuessPoolSignOutView(LoginRequiredMixin, GuessPoolMembershipMixin, generic.View):
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
                "Nenhum bolão público cadastrado... Que tal criar um agora mesmo? Basta clicar em <strong>Criar bolão</strong> e configurar como quiser 😎",
                "long",
            )
        return super().get(request, *args, **kwargs)


class PoolHomeView(LoginRequiredMixin, GuessPoolMembershipMixin, generic.TemplateView):
    template_name = "core/pool_home.html"


class GuessesView(LoginRequiredMixin, GuessPoolMembershipMixin, generic.View):
    def dispatch(self, request, *args, **kwargs):
        if self.pool.user_is_owner and not self.pool.user_is_guesser:
            return redirect_with_msg(
                self.request,
                "error",
                "Você não está cadastrado como palpiteiro. Acesse <strong>Gerenciar bolão</strong> e marque seu usuário como <strong>Palpiteiro</strong> para ter acesso à esta ação.",
                "long",
                self.pool,
            )

        return super().dispatch(request, *args, **kwargs)

    def get(self, *args, **kwargs):
        logger.info(
            f"{timezone.now()}: user {self.request.user} accessed the /palpites route"
        )

        open_matches = self.pool.get_open_matches()
        closed_matches = self.pool.get_closed_recent_matches()

        has_matches = open_matches.exists() or closed_matches.exists()
        if not has_matches:
            return redirect_with_msg(
                self.request,
                "error",
                "Não existem partidas para exibir neste momento ❌",
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

        closed_matches_and_guesses = []
        for match in closed_matches:
            try:
                guess = self.pool.guesses.get(
                    match=match,
                    guesser=self.guesser,
                )
            except Guess.DoesNotExist:
                guess = None

            closed_matches_and_guesses.append({"match": match, "guess": guess})

        return render(
            self.request,
            "core/guesses.html",
            {
                "pool": self.pool,
                "guess_forms": guess_forms,
                "closed_matches_and_guesses": closed_matches_and_guesses,
            },
        )

    def post(self, *args, **kwargs):
        guesses_data = dict(**self.request.POST)
        guesses_data.pop("csrfmiddlewaretoken")
        logger.info(
            f"{timezone.now()}: user {self.request.user} submitted following guesses: {guesses_data}"
        )

        for_all_pools = bool(self.request.POST.get("for_all_pools"))

        open_matches = self.pool.get_open_matches()
        closed_matches = self.pool.get_closed_recent_matches()

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

        closed_matches_and_guesses = []
        for match in closed_matches:
            try:
                guess = self.pool.guesses.get(
                    match=match,
                    guesser=self.guesser,
                )

            except Guess.DoesNotExist:
                guess = None

            closed_matches_and_guesses.append({"match": match, "guess": guess})

        messages.success(
            self.request,
            "Palpites salvos ✅",
            "temp-msg short-time-msg",
        )

        return render(
            self.request,
            "core/guesses.html",
            {
                "pool": self.pool,
                "guess_forms": guess_forms,
                "closed_matches_and_guesses": closed_matches_and_guesses,
            },
        )


class RankingView(LoginRequiredMixin, GuessPoolMembershipMixin, generic.TemplateView):
    template_name = "core/ranking.html"

    def get(self, *args, **kwargs):
        context = self.get_context_data(**kwargs)
        if context.get("no_guessers"):
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

        today = timezone.localdate()
        default_period = {
            "periodo": "semanal",
            "ano": today.year,
            "mes": today.month,
            "semana": str(today.isocalendar().week),
        }
        form_data = self.request.GET if self.request.GET else default_period
        form = RankingPeriodForm(form_data, pool=self.pool)
        form.is_valid()

        period_params = form.get_period_for_query()
        ranking_entries = self.pool.get_ranking_for_period(**period_params)

        context["period_form"] = form
        context["ranking_entries"] = ranking_entries

        if not self.pool.guessers.exists():
            context["no_guessers"] = True

        return context


class GuessesByPeriodView(LoginRequiredMixin, GuessPoolMembershipMixin, generic.View):
    template_name = "core/guesses_by_period.html"
    paginate_by = 50

    def get(self, request, *args, **kwargs):
        today = timezone.localdate()
        default_period = {
            "periodo": "semanal",
            "ano": today.year,
            "mes": today.month,
            "semana": str(today.isocalendar().week),
            "palpiteiro": self.guesser.id,
        }
        form = GuessesPeriodForm(request.GET or default_period, pool=self.pool)
        form.is_valid()

        query_params = form.get_period_for_query()
        guesses_qs = self.get_queryset(**query_params)
        total_score = guesses_qs.aggregate(total=Sum("score"))["total"] or 0

        paginator = Paginator(guesses_qs, self.paginate_by)
        page_number = request.GET.get("page")
        page_obj = paginator.get_page(page_number)

        if request.headers.get("x-requested-with") == "XMLHttpRequest":
            return render(
                request,
                "core/partials/guesses_table_body.html",
                {"guesses": page_obj, "page_obj": page_obj},
            )

        return render(
            request,
            self.template_name,
            {
                "pool": self.pool,
                "form": form,
                "guesses": page_obj,
                "page_obj": page_obj,
                "total_score": total_score,
            },
        )

    def get_queryset(self, guesser, year, month, week):
        filters = Q(guesser=guesser) & Q(match__date_time__lt=timezone.localtime())

        if year and not month and not week:
            filters &= Q(match__date_time__year=year)
        elif year and month and not week:
            filters &= Q(match__date_time__year=year, match__date_time__month=month)
        elif year and week:
            filters &= Q(match__date_time__year=year, match__date_time__week=week)

        return self.pool.guesses.filter(filters).order_by("-match__date_time")
