from datetime import timedelta
from http import HTTPStatus

from django.test import TestCase
from django.contrib.auth import get_user_model
from django.utils import timezone
from django.urls import reverse

from model_mommy import mommy

from ..models import Palpiteiro, Partida, Rodada


class PalpitarViewTests(TestCase):
    @classmethod
    def setUpTestData(cls) -> None:
        cls.user = get_user_model().objects.create(username="testuser")
        cls.palpiteiro = Palpiteiro.objects.create(usuario=cls.user)

    def setUp(self) -> None:
        self.client.force_login(self.user)

    def test_match_closed_for_guesses_half_hour_before(self):
        """Predictions must be unavailable half an hour before the
        match data_hora, so only one form should be in context of the
        get request response"""

        rodada = mommy.make(Rodada)

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

        response = self.client.get(reverse("core:palpitar"))
        forms = response.context["forms_palpites_abertos"]

        self.assertEquals(response.status_code, HTTPStatus.OK)
        self.assertEquals(Partida.objects.count(), 3)
        self.assertEquals(len(forms), 1)
        self.assertEquals(forms[0].partida, open_match)


class ClassificacaoViewTest(TestCase):
    ...
