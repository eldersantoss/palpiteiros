from django import forms
from django.contrib.auth.models import User


class UserRegistrationForm(forms.ModelForm):
    username = forms.CharField(
        max_length=150,
        label="Usuário",
        widget=forms.TextInput(
            attrs={"placeholder": "Somente letras, números e caracteres . @ + - _"}
        ),
    )
    first_name = forms.CharField(max_length=150, label="Nome")
    last_name = forms.CharField(max_length=150, label="Sobrenome", required=False)
    email = forms.EmailField(label="Email")
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
        fields = ("username", "first_name", "last_name", "email")

    def clean_password_confirmation(self):
        if self.cleaned_data["password_confirmation"] != self.cleaned_data["password"]:
            raise forms.ValidationError("As senhas são diferentes.")
        return self.cleaned_data["password_confirmation"]
