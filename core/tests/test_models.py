from datetime import timedelta

from django.core.exceptions import ValidationError
from django.test import TestCase
from django.utils import timezone
from model_mommy import mommy

from core.models import Palpite, Palpiteiro, Partida, Rodada

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
    def test_only_one_active_round_is_allowed(self):
        with self.assertRaises(ValidationError):
            mommy.make(Rodada, active=True)

    def test_round_detail_has_all_guessers_of_the_pool(self):
        """All guessers of the pool should be in the returned data"""

        round_ = Rodada.objects.filter(active=True).last()
        self.assertIsNotNone(round_)

        round_detail = round_.get_details(self.guesser01.usuario)
        guessers = [detail["guesser"] for detail in round_detail]
        self.assertCountEqual(guessers, self.guessers)

    def test_round_datail_has_all_matches_of_the_round(self):
        """All matches of the round should be in each dict of the
        returned data"""
        round_ = Rodada.objects.filter(active=True).last()
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
        round_ = Rodada.objects.filter(active=True).last()
        self.assertIsNotNone(round_)

        round_detail = round_.get_details(self.guesser01.usuario)
        for i in range(len(round_detail) - 1):
            self.assertGreaterEqual(
                round_detail[i]["round_score"],
                round_detail[i + 1]["round_score"],
            )

    def test_round_detail_has_correct_round_score_for_guessers(self):
        round_ = Rodada.objects.filter(active=True).last()
        self.assertIsNotNone(round_)
        for guess in Palpite.objects.all():
            guess.get_score()

        round_detail = round_.get_details(self.guesser01.usuario)
        self.assertEqual(round_detail[0]["round_score"], 34)
        self.assertEqual(round_detail[1]["round_score"], 22)
        self.assertEqual(round_detail[2]["round_score"], 0)

    def test_round_detail_has_omitted_guesses_for_open_matches(self):
        round_ = Rodada.objects.filter(active=True).last()
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


class GuessPoolModelTests(PalpiteirosTestCase):
    def test_number_of_teams(self):
        """pool01, pool02 and pool03 should have 8 teams each"""
        self.assertEqual(self.pool01.number_of_teams(), 8)
        self.assertEqual(self.pool02.number_of_teams(), 8)
        self.assertEqual(self.pool03.number_of_teams(), 8)

    def test_number_of_guessers(self):
        """pool01, pool02 should have 3 guessers and pool03 should
        have 2"""
        self.assertEqual(self.pool01.number_of_guessers(), 3)
        self.assertEqual(self.pool02.number_of_guessers(), 3)
        self.assertEqual(self.pool03.number_of_guessers(), 2)

    def test_get_update_or_create_guesses_before_create_any_guess(self):
        open_matches = self.pool01.get_update_or_create_guesses(self.pool01.owner)
        self.assertEqual(open_matches.count(), 1)
        self.assertTrue(all(not m.guess_form.is_bound for m in open_matches))

        open_matches = self.pool02.get_update_or_create_guesses(self.pool02.owner)
        self.assertEqual(open_matches.count(), 1)
        self.assertTrue(all(not m.guess_form.is_bound for m in open_matches))

        open_matches = self.pool03.get_update_or_create_guesses(self.pool03.owner)
        self.assertEqual(open_matches.count(), 2)
        self.assertTrue(all(not m.guess_form.is_bound for m in open_matches))

    def test_creating_exclusive_guesses(self):
        post_data = self._generate_post_data(self.pool01)
        self.pool01.get_update_or_create_guesses(self.pool01.owner, post_data)
        self.assertEqual(self.pool01.guesses.count(), 1)

        post_data = self._generate_post_data(self.pool02)
        self.pool02.get_update_or_create_guesses(
            self.pool02.owner, post_data
        )
        self.assertEqual(self.pool02.guesses.count(), 1)

        post_data = self._generate_post_data(self.pool03)
        self.pool03.get_update_or_create_guesses(self.pool03.owner, post_data)
        self.assertEqual(self.pool03.guesses.count(), 2)

        self.assertNotIn(self.pool01.guesses.get(), self.pool03.guesses.all())
        self.assertNotIn(self.pool02.guesses.get(), self.pool03.guesses.all())


    def test_creating_for_all_pools_guesses(self):
        post_data = self._generate_post_data(self.pool01, True)
        self.pool01.get_update_or_create_guesses(self.pool01.owner, post_data)
        self.assertEqual(self.pool01.guesses.count(), 1)
        self.assertEqual(self.pool02.guesses.count(), 0)
        self.assertEqual(self.pool03.guesses.count(), 1)
        self.assertIn(self.pool01.guesses.get(), self.pool03.guesses.all())

        post_data = self._generate_post_data(self.pool02, True)
        self.pool02.get_update_or_create_guesses(self.pool02.owner, post_data)
        self.assertEqual(self.pool01.guesses.count(), 1)
        self.assertEqual(self.pool02.guesses.count(), 1)
        self.assertEqual(self.pool03.guesses.count(), 1)
        self.assertNotIn(self.pool02.guesses.get(), self.pool03.guesses.all())

        post_data = self._generate_post_data(self.pool02, True)
        self.pool02.get_update_or_create_guesses(self.guesser01, post_data)
        self.assertEqual(self.pool01.guesses.count(), 1)
        self.assertEqual(self.pool02.guesses.count(), 2)
        self.assertEqual(self.pool03.guesses.count(), 2)
        self.assertIn(
            self.pool02.guesses.get(palpiteiro=self.guesser01),
            self.pool03.guesses.all(),
        )

        post_data = self._generate_post_data(self.pool03, True)
        self.pool03.get_update_or_create_guesses(self.pool03.owner, post_data)
        self.assertEqual(self.pool01.guesses.count(), 2)
        self.assertEqual(self.pool02.guesses.count(), 3)
        self.assertEqual(self.pool03.guesses.count(), 4)

        post_data = self._generate_post_data(self.pool03, True, 1)
        self.pool03.get_update_or_create_guesses(self.guesser01, post_data)
        self.assertEqual(self.pool03.guesses.count(), 4)

    def test_get_update_or_create_guesses_updating_guesses(self):
        ...

    def _generate_post_data(self, pool, for_all_pools=False, goals=0):
        post_data = {"for_all_pools": True} if for_all_pools else {}
        for m in pool.get_open_matches():
            post_data[f"gols_mandante_{m.id}"] = goals
            post_data[f"gols_visitante_{m.id}"] = goals
        return post_data

    def test_get_open_matches(self):
        """pool01, pool02 should have 1 open match and pool03 should
        have 2"""
        self.assertEqual(self.pool01.get_open_matches().count(), 1)
        self.assertEqual(self.pool02.get_open_matches().count(), 1)
        self.assertEqual(self.pool03.get_open_matches().count(), 2)

    def test_number_of_matches(self):
        """pool01, pool02 and pool03 should have 4 matches each"""
        self.assertEqual(self.pool01.number_of_matches(), 4)
        self.assertEqual(self.pool02.number_of_matches(), 4)
        self.assertEqual(self.pool03.number_of_matches(), 4)

    def test_get_matches(self):
        self.assertTrue(
            all([m.data_hora > self.pool01.created for m in self.pool01.get_matches()])
        )
        self.assertTrue(
            all(
                [
                    (
                        m.mandante in self.pool01.teams.all()
                        or m.visitante in self.pool01.teams.all()
                    )
                    for m in self.pool01.get_matches()
                ]
            )
        )

        self.assertTrue(
            all([m.data_hora > self.pool02.created for m in self.pool02.get_matches()])
        )
        self.assertTrue(
            all(
                [
                    (
                        m.mandante in self.pool02.teams.all()
                        or m.visitante in self.pool02.teams.all()
                    )
                    for m in self.pool02.get_matches()
                ]
            )
        )

        self.assertTrue(
            all([m.data_hora > self.pool03.created for m in self.pool03.get_matches()])
        )
        self.assertTrue(
            all(
                [
                    (
                        m.mandante in self.pool03.teams.all()
                        or m.visitante in self.pool03.teams.all()
                    )
                    for m in self.pool03.get_matches()
                ]
            )
        )

    def test_get_ranking_with_no_guesses(self):
        """Guessers of pool01, pool02 and pools3 should have your score
        attribute equals to 0"""

        # general period
        self.assertTrue(all([g.score == 0 for g in self.pool01.get_ranking(0, 0)]))
        self.assertTrue(all([g.score == 0 for g in self.pool02.get_ranking(0, 0)]))
        self.assertTrue(all([g.score == 0 for g in self.pool03.get_ranking(0, 0)]))

        # annual period
        year = timezone.now().year
        self.assertTrue(all([g.score == 0 for g in self.pool01.get_ranking(0, year)]))
        self.assertTrue(all([g.score == 0 for g in self.pool02.get_ranking(0, year)]))
        self.assertTrue(all([g.score == 0 for g in self.pool03.get_ranking(0, year)]))

        # monthly period
        month, year = timezone.now().month, timezone.now().year
        self.assertTrue(
            all([g.score == 0 for g in self.pool01.get_ranking(month, year)])
        )
        self.assertTrue(
            all([g.score == 0 for g in self.pool02.get_ranking(month, year)])
        )
        self.assertTrue(
            all([g.score == 0 for g in self.pool03.get_ranking(month, year)])
        )


    def test_get_ranking_with_exclusive_guesses(self):
        """
        equipes:
        ------- p1
        0 1
        2 3
        ------ p1-p3
        4 5
        6 7 (O)
        ------ p2-p3
        8 9 (O)
        10 11
        ------ p2
        12 13
        14 15

        placares:
        ------ p1
        0 0
        2 4
        ------ p1-p3
        4 8
        6 12 (O)
        ------ p2-p3
        8 16 (O)
        10 20
        ------ p2
        12 24
        14 28
        """
        self.pool01.guesses.add(Palpite.objects.create(
            palpiteiro=self.guesser01,
            partida=self.matches[0],
            gols_mandante=1,
            gols_visitante=1,
        ))
        self.pool01.guesses.add(Palpite.objects.create(
            palpiteiro=self.guesser01,
            partida=self.matches[1],
            gols_mandante=2,
            gols_visitante=4,
        ))
        self.pool01.guesses.add(Palpite.objects.create(
            palpiteiro=self.guesser01,
            partida=self.matches[2],
            gols_mandante=0,
            gols_visitante=8,
        ))
        self.pool01.guesses.add(Palpite.objects.create(
            palpiteiro=self.guesser01,
            partida=self.matches[3],
            gols_mandante=0,
            gols_visitante=1,
        ))

        self.pool01.guesses.add(Palpite.objects.create(
            palpiteiro=self.guesser03,
            partida=self.matches[0],
            gols_mandante=0,
            gols_visitante=0,
        ))
        self.pool01.guesses.add(Palpite.objects.create(
            palpiteiro=self.guesser03,
            partida=self.matches[1],
            gols_mandante=2,
            gols_visitante=3,
        ))
        self.pool01.guesses.add(Palpite.objects.create(
            palpiteiro=self.guesser03,
            partida=self.matches[2],
            gols_mandante=4,
            gols_visitante=0,
        ))
        self.pool01.guesses.add(Palpite.objects.create(
            palpiteiro=self.guesser03,
            partida=self.matches[3],
            gols_mandante=2,
            gols_visitante=1,
        ))


        for g in self.pool01.guesses.all():
            g.evaluate_and_consolidate()

        month, year = timezone.now().month, timezone.now().year
        ranking = self.pool01.get_ranking(month, year)
        self.assertEqual(ranking.get(id=self.guesser01.id).score, 23)
        self.assertEqual(ranking.get(id=self.guesser02.id).score, 0)
        self.assertEqual(ranking.get(id=self.guesser03.id).score, 16)


        open_match_without_result = mommy.make(
            Partida,
            rodada=[self.active_round],
            mandante=self.teams[0],
            visitante=self.teams[3],
            data_hora=timezone.now() + timedelta(hours=6),
        )
        self.assertIsNone(open_match_without_result.result_str)
        self.pool01.guesses.add(
            Palpite.objects.create(
                palpiteiro=self.guesser01,
                partida=open_match_without_result,
                gols_mandante=10,
                gols_visitante=10,
            )
        )
        month, year = 0, 0
        ranking = self.pool01.get_ranking(month, year)
        self.assertEqual(ranking.get(id=self.guesser01.id).score, 23)
        self.assertEqual(ranking.get(id=self.guesser02.id).score, 0)
        self.assertEqual(ranking.get(id=self.guesser03.id).score, 16)

        date_in_next_month = timezone.now() + timedelta(weeks=6)
        month, year = date_in_next_month.month, date_in_next_month.year
        ranking = self.pool01.get_ranking(month, year)
        self.assertEqual(ranking.get(id=self.guesser01.id).score, 0)
        self.assertEqual(ranking.get(id=self.guesser02.id).score, 0)
        self.assertEqual(ranking.get(id=self.guesser03.id).score, 0)

        for g in self.pool03.guesses.all():
            g.evaluate_and_consolidate()

        ranking = self.pool03.get_ranking(0, 0)
        self.assertEqual(ranking.get(id=self.guesser01.id).score, 0)
        with self.assertRaises(Palpiteiro.DoesNotExist):
            ranking.get(id=self.guesser02.id)
        self.assertEqual(ranking.get(id=self.guesser03.id).score, 0)
