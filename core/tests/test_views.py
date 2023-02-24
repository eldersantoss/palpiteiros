from datetime import timedelta
from http import HTTPStatus

from django.test import TestCase
from django.contrib.auth import get_user_model
from django.utils import timezone
from django.urls import reverse

from model_mommy import mommy

from ..models import Palpiteiro, Partida, Rodada, Palpite


class PalpitarViewTests(TestCase):
    @classmethod
    def setUpTestData(cls) -> None:
        cls.user = get_user_model().objects.create(username="testuser")
        cls.palpiteiro = Palpiteiro.objects.create(usuario=cls.user)

    def setUp(self) -> None:
        self.client.force_login(self.user)

    def test_no_guesser_found(self):
        """When no guesser is found the response should be a
        redirect to palpiteiro_nao_encontrado"""

        self.palpiteiro.delete()

        response = self.client.get(reverse("core:palpitar"))

        self.assertEquals(response.status_code, HTTPStatus.FOUND)
        self.assertRedirects(response, reverse("core:palpiteiro_nao_encontrado"))

    def test_no_round_found(self):
        """When no round is found the response should be a
        redirect to rodada_nao_encontrada"""

        response = self.client.get(reverse("core:palpitar"))

        self.assertEquals(response.status_code, HTTPStatus.FOUND)
        self.assertRedirects(response, reverse("core:rodada_nao_encontrada"))

    def test_no_open_matches(self):
        """When no open matches are found, the response should be a
        redirect to palpites_encerrados"""
        mommy.make(Rodada)

        response = self.client.get(reverse("core:palpitar"))

        self.assertEquals(response.status_code, HTTPStatus.FOUND)
        self.assertRedirects(response, reverse("core:palpites_encerrados"))

    def test_form_count_for_open_matches(self):
        """The number of forms in the context should be equals to the
        number of open matches"""
        rodada = mommy.make(Rodada)
        open_matches = mommy.make(
            Partida,
            _quantity=5,
            rodada=rodada,
            data_hora=timezone.now() + timedelta(minutes=60),
        )

        response = self.client.get(reverse("core:palpitar"))
        forms_palpites_abertos = response.context["forms_palpites_abertos"]

        self.assertEquals(response.status_code, HTTPStatus.OK)
        self.assertEquals(len(forms_palpites_abertos), len(open_matches))

    def test_populated_forms_for_open_matches_that_have_a_guess(self):
        """Forms for matches that already been filled out should
        still be filled in with the same values"""

        open_match = mommy.make(
            Partida,
            data_hora=timezone.now() + timedelta(minutes=60),
        )

        guess = mommy.make(
            Palpite,
            palpiteiro=self.palpiteiro,
            partida=open_match,
            gols_mandante=1,
            gols_visitante=0,
        )

        response = self.client.get(reverse("core:palpitar"))
        forms = response.context["forms_palpites_abertos"]

        self.assertEquals(len(forms), 1)

        palpite_form = forms[0]

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
        dados_palpites_encerrados = response.context["dados_palpites_encerrados"]
        forms_palpites_abertos = response.context["forms_palpites_abertos"]

        self.assertEquals(response.status_code, HTTPStatus.OK)
        self.assertEquals(Partida.objects.count(), 3)
        self.assertEquals(len(dados_palpites_encerrados), 2)
        self.assertEquals(len(forms_palpites_abertos), 1)
        self.assertEquals(forms_palpites_abertos[0].partida, open_match)

    def test_send_a_guess(self):
        """When send a guess for a open match via post request, a
        Palpite instance should be created"""

        open_match = mommy.make(
            Partida,
            data_hora=timezone.now() + timedelta(minutes=60),
        )
        number_of_guesses_before = Palpite.objects.count()

        self.client.post(
            reverse("core:palpitar"),
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


class ClassificacaoViewTest(TestCase):
    ...
