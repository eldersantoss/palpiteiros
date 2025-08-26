from datetime import date

from django import forms
from django.contrib.auth.models import User
from django.utils import timezone
from django.utils.translation import gettext as _

from core.models import Guesser


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
    PERIOD_CHOICES = (
        ("geral", "Geral"),
        ("anual", "Anual"),
        ("mensal", "Mensal"),
        ("semanal", "Semanal"),
    )

    periodo = forms.ChoiceField(label="Período", choices=PERIOD_CHOICES, required=False)
    ano = forms.ChoiceField(label="Ano", required=False)
    mes = forms.ChoiceField(label="Mês", required=False)
    semana = forms.ChoiceField(label="Semana", required=False)

    def __init__(self, *args, **kwargs):
        pool = kwargs.pop("pool", None)
        super().__init__(*args, **kwargs)

        # Populate year choices
        if pool:
            years = sorted(
                set(
                    pool.guesses.all()
                    .values_list("match__date_time__year", flat=True)
                    .distinct()
                ),
                reverse=True,
            )
        else:
            years = [timezone.localdate().year]

        self.fields["ano"].choices = [(y, str(y)) for y in years]

        # Populate month choices
        self.fields["mes"].choices = [
            (str(m), _(date(2000, m, 1).strftime("%B"))) for m in range(1, 13)
        ]

        # Populate week choices
        current_week = timezone.localdate().isocalendar().week
        self.fields["semana"].choices = [
            (str(w), f"Semana #{w}") for w in range(current_week, 0, -1)
        ]

    def get_period_for_query(self) -> dict:
        """
        Returns a dictionary with the parameters ready for the model query.
        """
        source = self.cleaned_data or self.initial or self.data

        period = source.get("periodo")
        if period in ["", None]:
            period = "semanal"

        year = source.get("ano")
        if year in ["", None]:
            year = timezone.localdate().year

        month = source.get("mes")
        if month in ["", None]:
            month = timezone.localdate().month

        week = source.get("semana")
        if week in ["", None]:
            week = timezone.localdate().isocalendar().week

        if period == "anual":
            return {"year": year, "month": 0, "week": 0}
        if period == "mensal":
            return {"year": year, "month": month, "week": 0}
        if period == "semanal":
            return {"year": year, "month": 0, "week": week}

        # Default to geral
        return {"year": 0, "month": 0, "week": 0}


class GuessesPeriodForm(forms.Form):
    PERIOD_CHOICES = (
        ("geral", "Geral"),
        ("anual", "Anual"),
        ("mensal", "Mensal"),
        ("semanal", "Semanal"),
    )

    periodo = forms.ChoiceField(label="Período", choices=PERIOD_CHOICES, required=False)
    ano = forms.ChoiceField(label="Ano", required=False)
    mes = forms.ChoiceField(label="Mês", required=False)
    semana = forms.ChoiceField(label="Semana", required=False)
    palpiteiro = forms.ChoiceField(label="Palpiteiro", required=False)

    def __init__(self, *args, **kwargs):
        pool = kwargs.pop("pool", None)
        super().__init__(*args, **kwargs)

        if pool:
            guessers = pool.guessers.all().order_by(
                "user__first_name", "user__username"
            )
            self.fields["palpiteiro"].choices = [
                (g.id, g.user.get_full_name() or g.user.username) for g in guessers
            ]

            years = sorted(
                set(
                    pool.guesses.all()
                    .values_list("match__date_time__year", flat=True)
                    .distinct()
                ),
                reverse=True,
            )
            self.fields["ano"].choices = [(y, str(y)) for y in years]

        self.fields["mes"].choices = [
            (str(m), _(date(2000, m, 1).strftime("%B"))) for m in range(1, 13)
        ]

        current_week = timezone.localdate().isocalendar().week
        self.fields["semana"].choices = [
            (str(w), f"Semana #{w}") for w in range(current_week, 0, -1)
        ]

    def get_period_for_query(self) -> dict:
        """
        Returns a dictionary with the parameters ready for the model query.
        """
        source = self.cleaned_data or self.initial or self.data

        period = source.get("periodo")
        if period in ["", None]:
            period = "semanal"

        year = source.get("ano")
        if year in ["", None]:
            year = timezone.localdate().year

        month = source.get("mes")
        if month in ["", None]:
            month = timezone.localdate().month

        week = source.get("semana")
        if week in ["", None]:
            week = timezone.localdate().isocalendar().week

        query = {"guesser": source.get("palpiteiro")}

        # Default to geral
        if period == "geral":
            query.update({"year": 0, "month": 0, "week": 0})
        if period == "anual":
            query.update({"year": year, "month": 0, "week": 0})
        if period == "mensal":
            query.update({"year": year, "month": month, "week": 0})
        if period == "semanal":
            query.update({"year": year, "month": 0, "week": week})

        return query
