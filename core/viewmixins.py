from django.shortcuts import get_object_or_404, redirect
from django.contrib import messages
from django.urls import reverse_lazy

from .models import GuessPool


class GuessPoolMembershipMixin(object):
    pool_slug_url_kwarg = "pool_slug"
    redirect_url = "core:index"

    def dispatch(self, request, *args, **kwargs):
        if not self.has_permission():
            return redirect(reverse_lazy(self.redirect_url))
        return super().dispatch(request, *args, **kwargs)

    def has_permission(self):
        pool = self.get_pool()
        if pool.guessers.filter(usuario=self.request.user).exists():
            return True
        messages.error(
            self.request,
            f"Você não está cadastrado no bolão {pool} ❌",
            "temp-msg mid-time-msg",
        )
        return False

    def get_pool(self):
        pool_slug = self.kwargs.get(self.pool_slug_url_kwarg)
        return get_object_or_404(GuessPool, slug=pool_slug)
