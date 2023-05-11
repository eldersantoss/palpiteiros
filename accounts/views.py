from django.shortcuts import render

from core.helpers import redirect_with_msg
from core.models import Guesser

from .forms import UserRegistrationForm


def register(request):
    if request.method == "POST":
        form = UserRegistrationForm(request.POST)
        if form.is_valid():
            new_user = form.save(commit=False)
            new_user.set_password(form.cleaned_data["password"])
            new_user.save()
            Guesser.objects.create(user=new_user)
            return redirect_with_msg(
                request,
                "success",
                "Usuário criado ✅",
                "short",
                "login",
            )
    else:
        form = UserRegistrationForm()
    return render(request, "registration/register.html", {"form": form})
