from datetime import timedelta
from http import HTTPStatus

from django.test import TestCase
from django.contrib.auth import get_user_model
from django.utils import timezone
from django.urls import reverse

from model_mommy import mommy

from ..models import Palpiteiro, Partida, Rodada, Palpite


class GuessesViewTests(TestCase):
    @classmethod
    def setUpTestData(cls) -> None:
        cls.user = get_user_model().objects.create(username="testuser")
        cls.palpiteiro = Palpiteiro.objects.create(usuario=cls.user)

    def setUp(self) -> None:
        self.client.force_login(self.user)

    def test_no_guesser_found(self):
        """When no guesser is found the response should be a redirect
        to index view"""

        self.palpiteiro.delete()

        response = self.client.get(reverse("core:guesses"))

        self.assertRedirects(response, reverse("core:index"), 302)

    def test_no_round_found(self):
        """When no round is found the response should be a
        redirect to index view"""

        response = self.client.get(reverse("core:guesses"))

        self.assertRedirects(response, reverse("core:index"), 302)

    def test_no_open_matches(self):
        """When no open matches are found, the response should be a
        redirect to index"""
        mommy.make(Rodada, active=True)

        response = self.client.get(reverse("core:guesses"))

        self.assertRedirects(response, reverse("core:index"), 302)

    def test_form_count_for_open_matches(self):
        """The number of forms in the context should be equals to the
        number of open matches"""
        rodada = mommy.make(Rodada, active=True)
        open_matches = mommy.make(
            Partida,
            _quantity=5,
            rodada=rodada,
            data_hora=timezone.now() + timedelta(minutes=60),
        )

        response = self.client.get(reverse("core:guesses"))

        open_matches_guess_forms = [
            om.guess_form for om in response.context["open_matches"]
        ]

        self.assertEquals(response.status_code, HTTPStatus.OK)
        self.assertEquals(len(open_matches_guess_forms), len(open_matches))

    def test_populated_forms_for_open_matches_that_have_a_guess(self):
        """Forms for matches that already been filled out should
        still be filled in with the same values"""

        rodada = mommy.make(Rodada, active=True)
        open_match = mommy.make(
            Partida,
            rodada=rodada,
            data_hora=timezone.now() + timedelta(minutes=60),
        )

        guess = mommy.make(
            Palpite,
            palpiteiro=self.palpiteiro,
            partida=open_match,
            gols_mandante=1,
            gols_visitante=0,
        )

        response = self.client.get(reverse("core:guesses"))
        open_matches_guess_forms = [
            om.guess_form for om in response.context["open_matches"]
        ]

        self.assertEquals(len(open_matches_guess_forms), 1)

        palpite_form = open_matches_guess_forms[0]

        self.assertEquals(response.status_code, HTTPStatus.OK)
        self.assertEquals(
            palpite_form.data[f"gols_mandante_{open_match.id}"],
            guess.gols_mandante,
        )
        self.assertEquals(
            palpite_form.data[f"gols_visitante_{open_match.id}"],
            guess.gols_visitante,
        )

    def test_match_closed_for_guesses_half_hour_before(self):
        """Predictions must be unavailable half an hour before the
        match data_hora, so one form referent to open match and two
        dicts referent to closed matches should be in context of the
        get request response"""

        rodada = mommy.make(Rodada, active=True)

        open_match = mommy.make(
            Partida, rodada=rodada, data_hora=timezone.now() + timedelta(minutes=31)
        )
        mommy.make(
            Partida,
            rodada=rodada,
            data_hora=timezone.now() + timedelta(minutes=30),
        )
        mommy.make(
            Partida,
            rodada=rodada,
            data_hora=timezone.now() - timedelta(minutes=30),
        )

        response = self.client.get(reverse("core:guesses"))
        closed_matches = response.context["closed_matches"]
        open_matches_guess_forms = [
            om.guess_form for om in response.context["open_matches"]
        ]

        self.assertEquals(response.status_code, HTTPStatus.OK)
        self.assertEquals(Partida.objects.count(), 3)
        self.assertEquals(len(closed_matches), 2)
        self.assertEquals(len(open_matches_guess_forms), 1)
        self.assertEquals(open_matches_guess_forms[0].partida, open_match)

    def test_send_a_guess(self):
        """When send a guess for a open match via post request, a
        Palpite instance should be created"""

        rodada = mommy.make(Rodada, active=True)
        open_match = mommy.make(
            Partida,
            rodada=rodada,
            data_hora=timezone.now() + timedelta(minutes=60),
        )
        number_of_guesses_before = Palpite.objects.count()

        self.client.post(
            reverse("core:guesses"),
            data={
                f"gols_mandante_{open_match.id}": 2,
                f"gols_visitante_{open_match.id}": 1,
            },
        )
        created_guess = Palpite.objects.last()

        self.assertEquals(Palpite.objects.count(), number_of_guesses_before + 1)
        self.assertEquals(created_guess.palpiteiro, self.palpiteiro)
        self.assertEquals(created_guess.partida, open_match)
        self.assertEquals(created_guess.gols_mandante, 2)
        self.assertEquals(created_guess.gols_visitante, 1)


class ClassificacaoViewTests(TestCase):
    @classmethod
    def setUpTestData(cls) -> None:
        cls.user = get_user_model().objects.create(username="testuser")
        cls.palpiteiro = Palpiteiro.objects.create(usuario=cls.user)

    def setUp(self) -> None:
        self.client.force_login(self.user)

    def test_period_form_in_context_data(self):
        response = self.client.get(reverse("core:ranking"))
        period_form = response.context.get("period_form")
        current_month = str(timezone.now().month)
        current_year = str(timezone.now().year)
        self.assertIsNotNone(period_form)
        self.assertTrue(period_form.is_valid())
        self.assertEquals(period_form.cleaned_data["mes"], current_month)
        self.assertEquals(period_form.cleaned_data["ano"], current_year)

        response = self.client.get(
            reverse("core:ranking"),
            data={"mes": 1, "ano": 2022},
        )
        period_form = response.context.get("period_form")
        self.assertIsNotNone(period_form)
        self.assertTrue(period_form.is_valid())
        self.assertEquals(period_form.cleaned_data["mes"], "1")
        self.assertEquals(period_form.cleaned_data["ano"], "2022")


class RoundDetailViewTests(TestCase):
    @classmethod
    def setUpTestData(cls) -> None:
        cls.user = get_user_model().objects.create(username="testuser")
        cls.guesser = Palpiteiro.objects.create(usuario=cls.user)

    def setUp(self) -> None:
        self.client.force_login(self.user)

    def test_correct_round_in_and_all_guessers_in_context(self):
        round_ = mommy.make(Rodada)
        guessers = mommy.make(Palpiteiro, _quantity=3) + [self.guesser]

        response = self.client.get(
            reverse(
                "core:round_details",
                kwargs={"id_rodada": round_.id},
            )
        )

        self.assertEqual(response.status_code, HTTPStatus.OK)
        self.assertIn("round", response.context)
        self.assertEqual(response.context["round"], round_)
        self.assertIn("round_details", response.context)
        self.assertEqual(len(guessers), len(response.context["round_details"]))
