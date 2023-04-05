from datetime import timedelta

from django.utils import timezone
from django.test import TestCase
from core.models import Partida, Rodada, Palpite

from model_mommy import mommy

from .base import PalpiteirosTestCase


class MatchModelTests(TestCase):
    def test_open_to_predictions_half_hour_before_match_time(self):
        """Should return True if the match time is at least half an
        hour before current time and False otherwise"""

        open_match = mommy.make(
            Partida,
            data_hora=timezone.now() + timedelta(minutes=31),
        )
        on_limit_closed_match = mommy.make(
            Partida,
            data_hora=timezone.now() + timedelta(minutes=30),
        )
        self.assertTrue(open_match.open_to_guesses())
        self.assertFalse(on_limit_closed_match.open_to_guesses())

    def test_save_is_evaluating_and_consolidating_guesses(self):
        """Save method should call evaluate_and_consolidate() for all
        guesses they are related to"""

        # Given a match and your guesses
        match = mommy.make(
            Partida,
            data_hora=timezone.now() - timedelta(hours=6),
        )
        spiked_guess = mommy.make(
            Palpite,
            partida=match,
            gols_mandante=2,
            gols_visitante=0,
        )
        partially_correct_guess = mommy.make(
            Palpite,
            partida=match,
            gols_mandante=3,
            gols_visitante=1,
        )

        # Initially the score must be zero for all guesses
        self.assertEqual(spiked_guess.get_score(), 0)
        self.assertEqual(partially_correct_guess.get_score(), 0)

        # When the match is updated
        match.gols_mandante = 2
        match.gols_visitante = 0
        match.save()

        # Then the guesses must have been evaluated and consolidated
        self.assertEqual(spiked_guess.get_score(), 10)
        self.assertTrue(spiked_guess.contabilizado)
        self.assertEqual(partially_correct_guess.get_score(), 3)
        self.assertTrue(partially_correct_guess.contabilizado)


class RoundModelTests(PalpiteirosTestCase):
    def test_round_detail_has_all_guessers_of_the_pool(self):
        """All guessers of the pool should be in the returned data"""

        round_ = Rodada.objects.last()
        self.assertIsNotNone(round_)

        round_detail = round_.get_details(self.guesser01.usuario)
        guessers = [detail["guesser"] for detail in round_detail]
        self.assertCountEqual(guessers, self.guessers)

    def test_round_datail_has_all_matches_of_the_round(self):
        """All matches of the round should be in each dict of the
        returned data"""
        round_ = Rodada.objects.last()
        self.assertIsNotNone(round_)

        round_detail = round_.get_details(self.guesser01.usuario)
        matches = [
            [
                detail_round_matches["match"]
                for detail_round_matches in detail["matches_and_guesses"]
            ]
            for detail in round_detail
        ]
        for match_set in matches:
            self.assertCountEqual(match_set, self.all_matches)

    def test_round_detail_guessers_are_correctly_ordered_by_round_score(self):
        round_ = Rodada.objects.last()
        self.assertIsNotNone(round_)

        round_detail = round_.get_details(self.guesser01.usuario)
        for i in range(len(round_detail) - 1):
            self.assertGreaterEqual(
                round_detail[i]["round_score"],
                round_detail[i + 1]["round_score"],
            )

    def test_round_detail_has_correct_round_score_for_guessers(self):
        round_ = Rodada.objects.last()
        self.assertIsNotNone(round_)
        for guess in Palpite.objects.all():
            guess.get_score()

        round_detail = round_.get_details(self.guesser01.usuario)
        self.assertEqual(round_detail[0]["round_score"], 34)
        self.assertEqual(round_detail[1]["round_score"], 22)
        self.assertEqual(round_detail[2]["round_score"], 0)

    def test_round_detail_has_omitted_guesses_for_open_matches(self):
        round_ = Rodada.objects.last()
        self.assertIsNotNone(round_)

        round_detail = round_.get_details(self.guesser01.usuario)

        for detail in round_detail:
            guesses = [
                match_and_guess["guess"]
                for match_and_guess in detail["matches_and_guesses"]
                if match_and_guess["guess"] is not None
            ]
            if detail["guesser"] == self.guesser01:
                self.assertEqual(len(guesses), len(self.all_matches))
            else:
                self.assertLessEqual(len(guesses), len(self.closed_matches))


class GuesserModelTests(PalpiteirosTestCase):
    def test_guessed_on_last_round(self):
        """PalpiteirosTestCasa provides a active round and three
        guessers of which two guessed (01 and 02), whose method must
        return True, and one that did not guess (03), whose the method
        must return False"""
        self.assertTrue(self.guesser01.guessed_on_last_round())
        self.assertTrue(self.guesser02.guessed_on_last_round())
        self.assertFalse(self.guesser03.guessed_on_last_round())
