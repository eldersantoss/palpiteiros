from django.shortcuts import render

from core.models import Palpiteiro

from .forms import UserRegistrationForm


def register(request):
    if request.method == "POST":
        form = UserRegistrationForm(request.POST)
        if form.is_valid():
            new_user = form.save(commit=False)
            new_user.set_password(form.cleaned_data["password"])
            new_user.save()
            Palpiteiro.objects.create(usuario=new_user)
            return render(
                request,
                "registration/register_done.html",
                {"new_user_name": new_user.first_name},
            )

    else:
        form = UserRegistrationForm()

    return render(
        request,
        "registration/register.html",
        {"form": form},
    )
