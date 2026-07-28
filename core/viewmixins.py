from django.db import transaction

from core.helpers import redirect_with_msg

from .forms import GuessForm
from .models import Guess, Guesser, GuessPool


class GuessPoolMembershipMixin:
    pool_slug_url_kwarg = "pool_slug"
    redirect_url = "core:index"

    def setup(self, request, *args, **kwargs):
        super().setup(request, *args, **kwargs)
        self.guesser = self.get_guesser()
        self.pool = self.get_pool()

        if self.guesser and self.pool:
            self.pool.user_is_owner = self.pool.owner == self.guesser
            self.pool.user_is_guesser = self.pool.guessers.contains(self.guesser)

        else:
            self.pool.user_is_owner = None
            self.pool.user_is_guesser = None

    def get_guesser(self) -> Guesser:
        return self.request.user.guesser if not self.request.user.is_anonymous else None

    def get_pool(self) -> GuessPool:
        pool_slug = self.kwargs.get(self.pool_slug_url_kwarg)
        return GuessPool.objects.select_related("owner").filter(slug=pool_slug).first()

    def dispatch(self, request, *args, **kwargs):
        if not self.has_permission():
            return redirect_with_msg(
                self.request,
                "error",
                f"Você não faz parte do bolão {self.pool} 🚫",
                "mid",
                self.redirect_url,
            )
        return super().dispatch(request, *args, **kwargs)

    def has_permission(self):
        return self.pool.user_is_owner or self.pool.user_is_guesser

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["pool"] = self.pool
        context["guesser"] = self.guesser
        return context


class GuessSavingMixin:
    def save_guesses(self, open_matches, post_data, for_all_pools, results):
        """
        Saves or updates guesses in bulk for open_matches based on post_data.
        Avoids redundant database writes and handles updates in-place when possible.
        """
        all_match_ids = [m.id for m in open_matches]

        # Prefetch existing guesses with their pools to avoid N+1 queries
        existing_guesses = {
            g.match_id: g
            for g in Guess.objects.filter(
                guesser=self.guesser,
                match_id__in=all_match_ids,
            ).prefetch_related("pools")
        }

        # Prefetch user's pools with their competitions and teams to resolve targets in memory
        guesser_pools = list(self.guesser.pools.all().prefetch_related("competitions", "teams"))

        # Pre-calculate pool competitions and teams sets of IDs to make in-memory lookups super fast
        pool_competitions_map = {pool.id: {c.id for c in pool.competitions.all()} for pool in guesser_pools}
        pool_teams_map = {pool.id: {t.id for t in pool.teams.all()} for pool in guesser_pools}

        has_new_guesses = False
        has_validation_errors = False

        for match in open_matches:
            guess_form = GuessForm(post_data, match=match)

            if guess_form.has_valid_guess_data():
                home_goals = guess_form.cleaned_data["home_goals"]
                away_goals = guess_form.cleaned_data["away_goals"]
                existing_guess = existing_guesses.get(match.id)

                # Resolve target pools in memory
                if for_all_pools:
                    target_pools = [
                        pool
                        for pool in guesser_pools
                        if (
                            match.competition_id in pool_competitions_map[pool.id]
                            or match.home_team_id in pool_teams_map[pool.id]
                            or match.away_team_id in pool_teams_map[pool.id]
                        )
                    ]
                else:
                    target_pools = [self.pool]

                # Determine if changes are needed
                with transaction.atomic():
                    change_made = False
                    if existing_guess:
                        # If identical goals and already associated, skip
                        current_pools = set(existing_guess.pools.all())
                        if (
                            existing_guess.home_goals == home_goals
                            and existing_guess.away_goals == away_goals
                            and current_pools.issuperset(target_pools)
                        ):
                            results["success"].append(match.id)
                            continue

                        other_pools = current_pools - set(target_pools)
                        if not other_pools:
                            # Update in-place
                            existing_guess.home_goals = home_goals
                            existing_guess.away_goals = away_goals
                            existing_guess.save()

                            # Add missing associations
                            missing_pools = set(target_pools) - current_pools
                            for pool in missing_pools:
                                pool.guesses.add(existing_guess)
                            change_made = True
                        else:
                            # Shared guess. Disassociate and create a new one.
                            for pool in target_pools:
                                if pool in current_pools:
                                    pool.guesses.remove(existing_guess)

                            new_guess = Guess.objects.create(
                                match=match,
                                guesser=self.guesser,
                                home_goals=home_goals,
                                away_goals=away_goals,
                            )
                            for pool in target_pools:
                                pool.guesses.add(new_guess)
                            change_made = True
                    else:
                        # New guess
                        new_guess = Guess.objects.create(
                            match=match,
                            guesser=self.guesser,
                            home_goals=home_goals,
                            away_goals=away_goals,
                        )
                        for pool in target_pools:
                            pool.guesses.add(new_guess)
                        change_made = True

                    if change_made:
                        has_new_guesses = True
                    results["success"].append(match.id)

            else:
                if not guess_form.is_valid():
                    has_validation_errors = True
                    errors_dict = {f: e[0] for f, e in guess_form.errors.items() if e}
                    errors_str = "; ".join(f"{f}: {e}" for f, e in errors_dict.items()) or "Erro de validação"
                    results["validation_errors"][str(match.id)] = errors_str

        if has_new_guesses:
            GuessPool.delete_orphans_guesses()

        return has_new_guesses, has_validation_errors
