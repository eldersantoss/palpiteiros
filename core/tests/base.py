from datetime import timedelta

from django.test import TestCase
from django.utils import timezone
from model_mommy import mommy

from core.models import Guesser, GuessPool, Match, Team


class GuessersTestCase(TestCase):
    @classmethod
    def setUpTestData(cls) -> None:
        # Guessers
        cls.guesser01 = mommy.make(Guesser)
        cls.guesser02 = mommy.make(Guesser)
        cls.guesser03 = mommy.make(Guesser)
        cls.guessers = [
            cls.guesser01,
            cls.guesser02,
            cls.guesser03,
        ]

        # Equipes
        cls.teams = mommy.make(Team, _quantity=16)

        # Bolões
        cls.pool01 = mommy.make(
            GuessPool, owner=cls.guesser01, guessers=cls.guessers, teams=cls.teams[:8]
        )
        cls.pool02 = mommy.make(
            GuessPool, owner=cls.guesser02, guessers=cls.guessers, teams=cls.teams[8:]
        )
        cls.pool03 = mommy.make(
            GuessPool,
            owner=cls.guesser03,
            guessers=[cls.guesser01],
            teams=cls.teams[4:12],
        )

        # Partidas
        cls.matches = []
        for i in range(0, len(cls.teams), 2):
            cls.matches.append(
                mommy.make(
                    Match,
                    home_team=cls.teams[i],
                    away_team=cls.teams[i + 1],
                    home_goals=i,
                    away_goals=2 * i,
                )
            )
        cls.open_matches = cls.matches[3:5]
        for m in cls.open_matches:
            m.date_time = timezone.now() + timedelta(hours=6)
            m.save()
        cls.closed_matches = list(set(cls.matches) - set(cls.open_matches))
