from datetime import timedelta
from http import HTTPStatus

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse_lazy
from django.utils import timezone
from model_mommy import mommy

from ..models import Guess, Guesser, GuessPool, Match, Rodada


class GuessesViewTests(TestCase):
    @classmethod
    def setUpTestData(cls) -> None:
        cls.user = get_user_model().objects.create(username="testuser")
        cls.guesser = Guesser.objects.create(user=cls.user)

    def setUp(self) -> None:
        self.client.force_login(self.user)

    def test_no_guesser_found(self):
        """When no guesser is found the response should be a redirect
        to index view"""

        self.guesser.delete()

        response = self.client.get(reverse_lazy("core:guesses"))

        self.assertRedirects(response, reverse_lazy("core:index"), 302)

    def test_no_round_found(self):
        """When no round is found the response should be a
        redirect to index view"""

        response = self.client.get(reverse_lazy("core:guesses"))

        self.assertRedirects(response, reverse_lazy("core:index"), 302)

    def test_no_open_matches(self):
        """When no open matches are found, the response should be a
        redirect to index"""
        mommy.make(Rodada, active=True)

        response = self.client.get(reverse_lazy("core:guesses"))

        self.assertRedirects(response, reverse_lazy("core:index"), 302)

    def test_form_count_for_open_matches(self):
        """The number of forms in the context should be equals to the
        number of open matches"""
        rodada = mommy.make(Rodada, active=True)
        open_matches = mommy.make(
            Match,
            _quantity=5,
            rodada=rodada,
            date_time=timezone.now() + timedelta(minutes=60),
        )

        response = self.client.get(reverse_lazy("core:guesses"))

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
            Match,
            rodada=rodada,
            date_time=timezone.now() + timedelta(minutes=60),
        )

        guess = mommy.make(
            Guess,
            guesser=self.guesser,
            match=open_match,
            home_goals=1,
            away_goals=0,
        )

        response = self.client.get(reverse_lazy("core:guesses"))
        open_matches_guess_forms = [
            om.guess_form for om in response.context["open_matches"]
        ]

        self.assertEquals(len(open_matches_guess_forms), 1)

        palpite_form = open_matches_guess_forms[0]

        self.assertEquals(response.status_code, HTTPStatus.OK)
        self.assertEquals(
            palpite_form.data[f"home_goals_{open_match.id}"],
            guess.home_goals,
        )
        self.assertEquals(
            palpite_form.data[f"away_goals_{open_match.id}"],
            guess.away_goals,
        )

    def test_match_closed_for_guesses_half_hour_before(self):
        """Predictions must be unavailable half an hour before the
        match date_time, so one form referent to open match and two
        dicts referent to closed matches should be in context of the
        get request response"""

        rodada = mommy.make(Rodada, active=True)

        open_match = mommy.make(
            Match, rodada=rodada, date_time=timezone.now() + timedelta(minutes=31)
        )
        mommy.make(
            Match,
            rodada=rodada,
            date_time=timezone.now() + timedelta(minutes=30),
        )
        mommy.make(
            Match,
            rodada=rodada,
            date_time=timezone.now() - timedelta(minutes=30),
        )

        response = self.client.get(reverse_lazy("core:guesses"))
        closed_matches = response.context["closed_matches"]
        open_matches_guess_forms = [
            om.guess_form for om in response.context["open_matches"]
        ]

        self.assertEquals(response.status_code, HTTPStatus.OK)
        self.assertEquals(Match.objects.count(), 3)
        self.assertEquals(len(closed_matches), 2)
        self.assertEquals(len(open_matches_guess_forms), 1)
        self.assertEquals(open_matches_guess_forms[0].match, open_match)

    def test_send_a_guess(self):
        """When send a guess for a open match via post request, a
        Palpite instance should be created"""

        rodada = mommy.make(Rodada, active=True)
        open_match = mommy.make(
            Match,
            rodada=rodada,
            date_time=timezone.now() + timedelta(minutes=60),
        )
        number_of_guesses_before = Guess.objects.count()

        self.client.post(
            reverse_lazy("core:guesses"),
            data={
                f"home_goals_{open_match.id}": 2,
                f"away_goals_{open_match.id}": 1,
            },
        )
        created_guess = Guess.objects.last()

        self.assertEquals(Guess.objects.count(), number_of_guesses_before + 1)
        self.assertEquals(created_guess.guesser, self.guesser)
        self.assertEquals(created_guess.match, open_match)
        self.assertEquals(created_guess.home_goals, 2)
        self.assertEquals(created_guess.away_goals, 1)


class ClassificacaoViewTests(TestCase):
    @classmethod
    def setUpTestData(cls) -> None:
        cls.user = get_user_model().objects.create(username="testuser")
        cls.guesser = Guesser.objects.create(user=cls.user)

    def setUp(self) -> None:
        self.client.force_login(self.user)

    def test_period_form_in_context_data(self):
        response = self.client.get(reverse_lazy("core:ranking"))
        period_form = response.context.get("period_form")
        current_month = str(timezone.now().month)
        current_year = str(timezone.now().year)
        self.assertIsNotNone(period_form)
        self.assertTrue(period_form.is_valid())
        self.assertEquals(period_form.cleaned_data["mes"], current_month)
        self.assertEquals(period_form.cleaned_data["ano"], current_year)

        response = self.client.get(
            reverse_lazy("core:ranking"),
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
        cls.guesser = mommy.make(Guesser)

    def setUp(self) -> None:
        self.client.force_login(self.guesser.user)

    def test_round_list(self):
        """Should have correct rounds in context, this is, all rounds
        excluding inactive future rounds"""
        pool = mommy.make(GuessPool, owner=self.guesser)
        visible_rounds = mommy.make(Rodada, pool=pool, _quantity=5)
        [mommy.make(Match, rodada=[vr]) for vr in visible_rounds[1:]]
        visible_rounds.pop(0)
        invisible_round = mommy.make(Rodada, pool=pool)
        mommy.make(
            Match,
            date_time=timezone.now() + timedelta(days=1),
            rodada=[invisible_round],
        )

        response = self.client.get(
            reverse_lazy(
                "core:round_list",
                kwargs={"pool_slug": pool.slug},
            )
        )

        self.assertEqual(response.status_code, HTTPStatus.OK)
        self.assertCountEqual(visible_rounds, response.context["rodadas"])

    def test_round_detail_has_correct_context_data(self):
        """Should have corrects round and round_detail in context"""
        guessers = mommy.make(Guesser, _quantity=3) + [self.guesser]
        pool = mommy.make(GuessPool, owner=self.guesser, guessers=guessers)
        round_ = mommy.make(Rodada, pool=pool)

        response = self.client.get(
            reverse_lazy(
                "core:round_details",
                kwargs={
                    "pool_slug": pool.slug,
                    "round_slug": round_.slug,
                },
            )
        )

        self.assertEqual(response.status_code, HTTPStatus.OK)
        self.assertIn("round", response.context)
        self.assertEqual(response.context["round"], round_)
        self.assertIn("round_details", response.context)
        self.assertEqual(len(guessers), len(response.context["round_details"]))
