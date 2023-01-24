from django import forms


class BasePalpiteForm(forms.Form):
    def __init__(self, *args, **kwargs):
        self.partida = kwargs.pop("partida")
        super().__init__(*args, **kwargs)
        self.label_suffix = ""
        self["gols_mandante"].label = self.partida.mandante.nome
        self["gols_mandante"].html_name += f"_{self.partida.id}"
        self["gols_visitante"].label = self.partida.visitante.nome
        self["gols_visitante"].html_name += f"_{self.partida.id}"


class EnabledPalpiteForm(BasePalpiteForm):
    gols_mandante = forms.IntegerField(min_value=0)
    gols_visitante = forms.IntegerField(min_value=0)


class DisabledPalpiteForm(BasePalpiteForm):
    gols_mandante = forms.IntegerField(min_value=0, disabled=True, required=False)
    gols_visitante = forms.IntegerField(min_value=0, disabled=True, required=False)
