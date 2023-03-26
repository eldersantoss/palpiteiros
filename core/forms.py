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
    GERAL = "0"
    ANO_2022 = "2022"
    ANO_2023 = "2023"
    ANO_2024 = "2024"
    YEAR_CHOICE = (
        (GERAL, "Geral"),
        (ANO_2022, "2022"),
        (ANO_2023, "2023"),
        (ANO_2024, "2024"),
    )

    ANUAL = "0"
    JANEIRO = "1"
    FEVEREIRO = "2"
    MARCO = "3"
    ABRIL = "4"
    MAIO = "5"
    JUNHO = "6"
    JULHO = "7"
    AGOSTO = "8"
    SETEMBRO = "9"
    OUTUBRO = "10"
    NOVEMBRO = "11"
    DEZEMBRO = "12"
    MONTH_CHOICES = (
        (ANUAL, "Anual"),
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
            if cd["ano"] == self.GERAL and cd["mes"] != self.ANUAL:
                cd["mes"] = self.ANUAL
        return cd
