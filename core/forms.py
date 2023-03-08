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


class RankingPeriodForm(forms.Form):
    GERAL = 0

    YEAR_CHOICE = (
        (GERAL, "Geral"),
        (2022, "2022"),
        (2023, "2023"),
        (2024, "2024"),
    )

    JANEIRO = 1
    FEVEREIRO = 2
    MARCO = 3
    ABRIL = 4
    MAIO = 5
    JUNHO = 6
    JULHO = 7
    AGOSTO = 8
    SETEMBRO = 9
    OUTUBRO = 10
    NOVEMBRO = 11
    DEZEMBRO = 12

    MONTH_CHOICES = (
        (GERAL, "Anual"),
        (JANEIRO, "Janeiro"),
        (FEVEREIRO, "Fevereiro"),
        (MARCO, "Março"),
        (ABRIL, "Abril"),
        (MAIO, "Maio"),
        (JUNHO, "Junho"),
        (JULHO, "Julho"),
        (AGOSTO, "Agosto"),
        (SETEMBRO, "Setembro"),
        (OUTUBRO, "Outrubro"),
        (NOVEMBRO, "Novembro"),
        (DEZEMBRO, "Dezembro"),
    )

    ano = forms.ChoiceField(
        label="Temporada",
        label_suffix="",
        choices=YEAR_CHOICE,
    )
    mes = forms.ChoiceField(
        label="Mês",
        label_suffix="",
        choices=MONTH_CHOICES,
    )

    def clean(self):
        cd = super().clean()
        if not self.errors:
            if cd["ano"] == "0" and cd["mes"] != "0":
                cd["mes"] = "0"
        return cd
