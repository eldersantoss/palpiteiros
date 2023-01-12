from django import forms
from django.contrib.auth.models import User


class UserRegistrationForm(forms.ModelForm):

    password = forms.CharField(
        label="Senha",
        widget=forms.PasswordInput,
    )
    password_confirmation = forms.CharField(
        label="Confirme sua senha",
        widget=forms.PasswordInput,
    )

    class Meta:
        model = User
        fields = ("username", "first_name", "email")

    def clean_password_confirmation(self):
        if self.cleaned_data["password_confirmation"] != self.cleaned_data["password"]:
            raise forms.ValidationError("As senhas são diferentes.")
        return self.cleaned_data["password_confirmation"]
