from typing import Literal

from django.contrib import messages
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse_lazy

from .models import GuessPool


class GuessPoolMembershipMixin:
    pool_slug_url_kwarg = "pool_slug"
    redirect_url = "core:index"

    def setup(self, request, *args, **kwargs):
        super().setup(request, *args, **kwargs)
        self.guesser = self.get_guesser()
        self.pool = self.get_pool()
        self.pool.user_is_owner = self.pool.owner == self.guesser
        self.pool.user_is_guesser = self.pool.guessers.filter(
            id=self.guesser.id
        ).exists()

    def get_guesser(self):
        return self.request.user.palpiteiro

    def get_pool(self):
        pool_slug = self.kwargs.get(self.pool_slug_url_kwarg)
        return get_object_or_404(GuessPool, slug=pool_slug)

    def dispatch(self, request, *args, **kwargs):
        if not self.has_permission():
            messages.error(
                self.request,
                f"Você não está cadastrado no bolão {self.pool} ❌",
                "temp-msg mid-time-msg",
            )
            return redirect(reverse_lazy(self.redirect_url))
        return super().dispatch(request, *args, **kwargs)

    def has_permission(self):
        return self.pool.user_is_owner or self.pool.user_is_guesser

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["pool"] = self.pool
        context["guesser"] = self.guesser
        return context

    def redirect_to_pool_home_with_error_msg(
        self,
        msg: str,
        msg_duration: Literal["short", "mid", "long"] = "short",
    ):
        extra_tags = f"temp-msg {msg_duration}-time-msg"
        messages.error(self.request, msg, extra_tags)
        return redirect(self.pool.get_absolute_url())
