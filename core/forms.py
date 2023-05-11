from django import forms
from django.utils import timezone
from django.utils.translation import gettext as _

from core.models import GuessPool


class GuessForm(forms.Form):
    gols_mandante = forms.IntegerField(min_value=0)
    gols_visitante = forms.IntegerField(min_value=0)

    def __init__(self, *args, **kwargs):
        self.partida = kwargs.pop("partida")
        super().__init__(*args, **kwargs)
        self.label_suffix = ""
        self["gols_mandante"].label = self.partida.mandante.nome
        self["gols_mandante"].html_name += f"_{self.partida.id}"
        self["gols_visitante"].label = self.partida.visitante.nome
        self["gols_visitante"].html_name += f"_{self.partida.id}"


class RankingPeriodForm(forms.Form):
    GERAL = "0"
    years = set(
        [year["created__year"] for year in GuessPool.objects.values("created__year")]
    )
    YEAR_CHOICE = [(GERAL, "Geral")] + [(str(year), str(year)) for year in years]

    MONTH_CHOICES = [(GERAL, "Anual")] + [
        (str(m), _(timezone.now().replace(month=m).strftime("%B")))
        for m in range(1, 13)
    ]

    MENSAL = "13"
    WEEK_CHOICE = [(GERAL, "Anual"), (MENSAL, "Mensal")]
    WEEK_CHOICE += [(week, f"Rodada #{week}") for week in range(1, 53)]

    ano = forms.ChoiceField(
        label="1. Temporada",
        label_suffix="",
        choices=YEAR_CHOICE,
    )
    mes = forms.ChoiceField(
        label="2. Mês",
        label_suffix="",
        choices=MONTH_CHOICES,
    )
    rodada = forms.ChoiceField(
        label="3. Rodada",
        label_suffix="",
        choices=WEEK_CHOICE,
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def clean(self):
        cd = super().clean()

        if not self.errors:
            year = cd["ano"]
            month = cd["mes"]

            """
            Quando year == GERAL, os demais campos assumem o valor geral
            e têm suas choices restritas somente para GERAL, resultando no
            período de classificação GERAL
            """
            if year == self.GERAL:
                self.fields["mes"].choices = [(self.GERAL, "Geral")]
                self.fields["rodada"].choices = [(self.GERAL, "Geral")]
                cd["mes"] = self.GERAL
                cd["rodada"] = self.GERAL

            else:
                """
                Quando year != GERAL, mas month == GERAL, o campo round_
                assume o valor geral e tem suas choices restritas somente
                para GERAL, resultando no período de classificação ANUAL
                """
                if month == self.GERAL:
                    self.fields["rodada"].choices = [(self.GERAL, "Anual")]
                    cd["rodada"] = self.GERAL

                else:
                    """
                    Quando year != GERAL e month != GERAL, o campo round_
                    é liberado para assumir valores no intervalo entre que
                    compreende o número das semanas do mês selecionado,
                    resultando nos períodos de classificação MENSAL ou
                    SEMANAL
                    """
                    weeks = [
                        week
                        for week in range(1, 53)
                        if timezone.datetime.fromisocalendar(
                            int(year), int(week), 1
                        ).month
                        == int(month)
                    ]

                    week_choices = [(week, f"Rodada #{week}") for week in weeks]

                    self.fields["rodada"].choices = [
                        (self.GERAL, "Mensal")
                    ] + week_choices

        return cd

    def _week_not_in_selected_month(self, year, month, week) -> bool:
        return month != timezone.datetime.fromisocalendar(year, week, 1).month

    def _get_week_for_selected_month(self, year: int, month: int) -> str:
        return str(timezone.now().replace(year=year, month=month).isocalendar().week)

    def _get_month_for_selected_week(
        self, selected_year: int, selected_week: int
    ) -> str:
        return str(
            timezone.datetime.fromisocalendar(selected_year, selected_week, 1).month
        )
