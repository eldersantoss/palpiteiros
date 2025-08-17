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
    YEAR_CHOICES = []
    MONTH_CHOICES = []
    WEEK_CHOICES = []

    ALL_TIMES_VALUE = "0"  # Valor para "Geral", "Anual", "Mensal"

    ano = forms.ChoiceField(
        label="1. Temporada",
        choices=YEAR_CHOICES,
    )
    mes = forms.ChoiceField(
        label="2. Mês",
        choices=MONTH_CHOICES,
    )
    semana = forms.ChoiceField(
        label="3. Semana",
        choices=WEEK_CHOICES,
    )

    def __init__(self, *args, **kwargs):
        # Intercepta os dados da requisição ANTES da validação.
        if args:
            data = args[0].copy()  # Cria uma cópia mutável do QueryDict
            year_selection = data.get("ano")
            month_selection = data.get("mes")

            # Regra 1: Se "Geral" for selecionado, força os campos filhos para "Geral".
            if year_selection == self.ALL_TIMES_VALUE:
                data["mes"] = self.ALL_TIMES_VALUE
                data["semana"] = self.ALL_TIMES_VALUE

            # Regra 2: Se "Anual" for selecionado, força o campo filho para "Anual".
            elif month_selection == self.ALL_TIMES_VALUE:
                data["semana"] = self.ALL_TIMES_VALUE

            # Substitui os argumentos originais com os dados corrigidos.
            args = (data,) + args[1:]

        super().__init__(*args, **kwargs)
        self._setup_dynamic_choices()

    def _setup_dynamic_choices(self):
        # Popula as escolhas de ano
        years = sorted(
            set(
                [y["created__year"] for y in GuessPool.objects.values("created__year")]
                + [date.today().year]
            ),
            reverse=True,
        )
        self.fields["ano"].choices = [(self.ALL_TIMES_VALUE, "Geral")] + [
            (str(y), str(y)) for y in years
        ]

        # Popula as escolhas de mês
        self.fields["mes"].choices = [(self.ALL_TIMES_VALUE, "Anual")] + [
            (str(m), _(date(2000, m, 1).strftime("%B"))) for m in range(1, 13)
        ]

        # Lógica para ajustar as choices com base nos dados (agora corrigidos)
        source = self.data or self.initial or {}
        year = source.get("ano")
        month = source.get("mes")

        if year == self.ALL_TIMES_VALUE:
            self.fields["mes"].choices = [(self.ALL_TIMES_VALUE, "Geral")]
            self.fields["semana"].choices = [(self.ALL_TIMES_VALUE, "Geral")]
        elif month and month != self.ALL_TIMES_VALUE:
            try:
                # Calcula as semanas para o mês/ano selecionado
                weeks_in_month = set()
                first_day = date(int(year), int(month), 1)
                last_day = (
                    first_day.replace(day=28) + timezone.timedelta(days=4)
                ).replace(day=1) - timezone.timedelta(days=1)

                current_day = first_day
                while current_day <= last_day:
                    weeks_in_month.add(current_day.isocalendar().week)
                    current_day += timezone.timedelta(days=1)

                week_choices = [
                    (str(w), f"Semana #{w}") for w in sorted(list(weeks_in_month))
                ]
                self.fields["semana"].choices = [
                    (self.ALL_TIMES_VALUE, "Mensal")
                ] + week_choices
            except (ValueError, TypeError):
                self.fields["semana"].choices = [(self.ALL_TIMES_VALUE, "Anual")]
        else:  # Ano selecionado, mas mês é "Anual"
            self.fields["semana"].choices = [(self.ALL_TIMES_VALUE, "Anual")]

    def get_period_for_query(self) -> dict:
        """
        Retorna um dicionário com os parâmetros prontos para a consulta no modelo.
        """
        # Garante que cleaned_data seja populado se o form foi submetido
        self.is_valid()

        # Usa cleaned_data se disponível, senão usa initial (primeira carga) ou data.
        source = self.cleaned_data or self.initial or self.data

        year = int(source.get("ano", 0))
        month = int(source.get("mes", 0))
        week = int(source.get("semana", 0))

        # Tradução dos valores do formulário para os valores do modelo
        if year == 0:  # Geral
            return {"year": 0, "month": 0, "week": 0}
        if month == 0:  # Anual
            return {"year": year, "month": 0, "week": 0}
        if week == 0:  # Mensal
            return {"year": year, "month": month, "week": 0}

        # Semanal
        return {"year": year, "month": month, "week": week}
