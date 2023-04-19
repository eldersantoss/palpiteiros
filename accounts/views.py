from django.contrib import messages
from django.shortcuts import redirect, render
from django.urls import reverse_lazy

from core.models import Palpiteiro

from .forms import UserRegistrationForm


def register(request):
    if request.method == "POST":
        form = UserRegistrationForm(request.POST)
        if form.is_valid():
            new_user = form.save(commit=False)
            new_user.set_password(form.cleaned_data["password"])
            new_user.save()
            messages.success(
                request,
                "Usuário criado ✅",
                "temp-msg short-time-msg",
            )
            Palpiteiro.objects.create(usuario=new_user)
            return redirect(reverse_lazy("login"))
    else:
        form = UserRegistrationForm()

    return render(
        request,
        "registration/register.html",
        {"form": form},
    )
