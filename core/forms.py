from datetime import date

from django import forms
from django.contrib.auth.models import User
from django.utils import timezone
from django.utils.translation import gettext as _

from core.models import Guesser, GuessPool


class UserEditForm(forms.ModelForm):
    class Meta:
        model = User
        fields = ("first_name", "last_name", "email")


class GuesserEditForm(forms.ModelForm):
    class Meta:
        model = Guesser
        fields = ("supported_team", "receive_notifications")


class GuessForm(forms.Form):
    home_goals = forms.IntegerField(min_value=0)
    away_goals = forms.IntegerField(min_value=0)

    def __init__(self, *args, **kwargs):
        self.match = kwargs.pop("match")
        super().__init__(*args, **kwargs)
        self.label_suffix = ""
        self["home_goals"].label = self.match.home_team.name
        self["home_goals"].html_name += f"_{self.match.id}"
        self["away_goals"].label = self.match.away_team.name
        self["away_goals"].html_name += f"_{self.match.id}"


class RankingPeriodForm(forms.Form):
    YEAR_CHOICE = []
    MONTH_CHOICES = []
    WEEK_CHOICES = []

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
        choices=WEEK_CHOICES,
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._setup_form_choices()

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
            if year == self.ALL_TIMES:
                self.fields["mes"].choices = [(self.ALL_TIMES, "Geral")]
                self.fields["rodada"].choices = [(self.ALL_TIMES, "Geral")]
                cd["mes"] = self.ALL_TIMES
                cd["rodada"] = self.ALL_TIMES

            else:
                """
                Quando year != GERAL, mas month == GERAL, o campo round_
                assume o valor geral e tem suas choices restritas somente
                para GERAL, resultando no período de classificação ANUAL
                """
                if month == self.ALL_TIMES:
                    self.fields["rodada"].choices = [(self.ALL_TIMES, "Anual")]
                    cd["rodada"] = self.ALL_TIMES

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

                    week_choices = [
                        (week, f"Rodada #{week}") for week in weeks
                    ]
                    self.fields["rodada"].choices = [
                        (self.ALL_TIMES, "Mensal")
                    ] + week_choices

        return cd

    def _setup_form_choices(self):
        self.ALL_TIMES = "0"
        self.MONTHLY = "13"

        years = set(
            [
                year["created__year"]
                for year in GuessPool.objects.values("created__year")
            ]
            + [date.today().year]
        )
        self.YEAR_CHOICE = [(self.ALL_TIMES, "Geral")] + [
            (str(year), str(year)) for year in years
        ]
        self.fields["ano"].choices = self.YEAR_CHOICE

        self.MONTH_CHOICES = [(self.ALL_TIMES, "Anual")] + [
            (str(m), _(timezone.now().replace(day=1, month=m).strftime("%B")))
            for m in range(1, 13)
        ]
        self.fields["mes"].choices = self.MONTH_CHOICES

        self.WEEK_CHOICES = [
            (self.ALL_TIMES, "Anual"),
            (self.MONTHLY, "Mensal"),
        ] + [(week, f"Rodada #{week}") for week in range(1, 53)]
        self.fields["rodada"].choices = self.WEEK_CHOICES

    def _week_not_in_selected_month(self, year, month, week) -> bool:
        return month != timezone.datetime.fromisocalendar(year, week, 1).month

    def _get_week_for_selected_month(self, year: int, month: int) -> str:
        return str(
            timezone.now().replace(year=year, month=month).isocalendar().week
        )

    def _get_month_for_selected_week(
        self, selected_year: int, selected_week: int
    ) -> str:
        return str(
            timezone.datetime.fromisocalendar(
                selected_year, selected_week, 1
            ).month
        )
