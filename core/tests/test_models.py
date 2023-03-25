from datetime import timedelta

from django.test import TestCase
from django.utils import timezone

from model_mommy import mommy

from ..models import Partida


class PartidaModelTests(TestCase):
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
