from core.helpers import redirect_with_msg

from .models import Guesser, GuessPool


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
        return GuessPool.objects.filter(slug=pool_slug).first()

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
