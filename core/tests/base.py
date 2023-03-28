from datetime import timedelta

from django.test import TestCase
from django.utils import timezone
from model_mommy import mommy

from core.models import Palpiteiro, Rodada, Partida, Palpite


class PalpiteirosTestCase(TestCase):
    @classmethod
    def setUpTestData(cls) -> None:
        # Palpiteiros
        cls.guesser01 = mommy.make(Palpiteiro)
        cls.guesser02 = mommy.make(Palpiteiro)
        cls.guesser03 = mommy.make(Palpiteiro)
        cls.guessers = [
            cls.guesser01,
            cls.guesser02,
            cls.guesser03,
        ]

        # Rodadas e Partidas
        cls.round = mommy.make(Rodada)
        cls.open_matches = mommy.make(
            Partida,
            _quantity=3,
            rodada=cls.round,
            data_hora=timezone.now() + timedelta(hours=6),
        )
        cls.closed_match1_double_home_1_x_0_away = mommy.make(
            Partida,
            rodada=cls.round,
            gols_mandante=1,
            gols_visitante=0,
            pontuacao_dobrada=True,
        )
        cls.closed_match2_home_0_x_0_away = mommy.make(
            Partida,
            rodada=cls.round,
            gols_mandante=0,
            gols_visitante=0,
        )
        cls.closed_match3_home_1_x_2_away = mommy.make(
            Partida,
            rodada=cls.round,
            gols_mandante=1,
            gols_visitante=2,
        )
        cls.closed_match4_home_0_x_2_away = mommy.make(
            Partida,
            rodada=cls.round,
            gols_mandante=0,
            gols_visitante=2,
        )
        cls.closed_match5_home_2_x_2_away = mommy.make(
            Partida,
            rodada=cls.round,
            gols_mandante=2,
            gols_visitante=2,
        )
        cls.closed_match6_home_4_x_2_away = mommy.make(
            Partida,
            rodada=cls.round,
            gols_mandante=4,
            gols_visitante=2,
        )
        cls.closed_matches = [
            cls.closed_match1_double_home_1_x_0_away,
            cls.closed_match2_home_0_x_0_away,
            cls.closed_match3_home_1_x_2_away,
            cls.closed_match4_home_0_x_2_away,
            cls.closed_match5_home_2_x_2_away,
            cls.closed_match6_home_4_x_2_away,
        ]
        cls.all_matches = cls.open_matches + cls.closed_matches

        # Palpites
        # Guesser01
        for idx, match in enumerate(cls.open_matches):
            mommy.make(
                Palpite,
                palpiteiro=cls.guesser01,
                partida=match,
                gols_mandante=idx,
                gols_visitante=idx,
            )
        # Acerto cravada dobrada (20 pontos)
        cls.guess1_guesser1_home_1_x_0_away = mommy.make(
            Palpite,
            palpiteiro=cls.guesser01,
            partida=cls.closed_match1_double_home_1_x_0_away,
            gols_mandante=1,
            gols_visitante=0,
        )
        # Acerto empate (5 pontos)
        cls.guess2_guesser1_home_1_x_1_away = mommy.make(
            Palpite,
            palpiteiro=cls.guesser01,
            partida=cls.closed_match2_home_0_x_0_away,
            gols_mandante=1,
            gols_visitante=1,
        )
        # Acerto parcial COM gols (5 pontos)
        cls.guess3_guesser1_home_1_x_3_away = mommy.make(
            Palpite,
            palpiteiro=cls.guesser01,
            partida=cls.closed_match3_home_1_x_2_away,
            gols_mandante=1,
            gols_visitante=3,
        )
        # Acerto parcial SEM gols (3 pontos)
        cls.guess4_guesser1_home_2_x_3_away = mommy.make(
            Palpite,
            palpiteiro=cls.guesser01,
            partida=cls.closed_match4_home_0_x_2_away,
            gols_mandante=2,
            gols_visitante=3,
        )
        # Acerto somente gols (1 ponto)
        cls.guess5_guesser1_home_2_x_0_away = mommy.make(
            Palpite,
            palpiteiro=cls.guesser01,
            partida=cls.closed_match5_home_2_x_2_away,
            gols_mandante=2,
            gols_visitante=0,
        )
        # Erro (0 pontos)
        cls.guess6_guesser1_home_0_x_1_away = mommy.make(
            Palpite,
            palpiteiro=cls.guesser01,
            partida=cls.closed_match6_home_4_x_2_away,
            gols_mandante=0,
            gols_visitante=1,
        )

        # Guesser02
        for idx, match in enumerate(cls.open_matches):
            mommy.make(
                Palpite,
                palpiteiro=cls.guesser02,
                partida=match,
                gols_mandante=idx,
                gols_visitante=idx,
            )
        # Acerto somente gols (2 pontos)
        cls.guess1_guesser2_home_1_x_1_away = mommy.make(
            Palpite,
            palpiteiro=cls.guesser02,
            partida=cls.closed_match1_double_home_1_x_0_away,
            gols_mandante=1,
            gols_visitante=1,
        )
        # Acerto empate (5 pontos)
        cls.guess2_guesser2_home_1_x_1_away = mommy.make(
            Palpite,
            palpiteiro=cls.guesser02,
            partida=cls.closed_match2_home_0_x_0_away,
            gols_mandante=1,
            gols_visitante=1,
        )
        # Acerto parcial COM gol (5 pontos)
        cls.guess3_guesser2_home_0_x_2_away = mommy.make(
            Palpite,
            palpiteiro=cls.guesser02,
            partida=cls.closed_match3_home_1_x_2_away,
            gols_mandante=0,
            gols_visitante=2,
        )
        # Erro (0 pontos)
        cls.guess5_guesser2_home_1_x_0_away = mommy.make(
            Palpite,
            palpiteiro=cls.guesser02,
            partida=cls.closed_match5_home_2_x_2_away,
            gols_mandante=1,
            gols_visitante=0,
        )
        # Acerto cravada (10 pontos)
        cls.guess6_guesser2_home_4_x_2_away = mommy.make(
            Palpite,
            palpiteiro=cls.guesser02,
            partida=cls.closed_match6_home_4_x_2_away,
            gols_mandante=4,
            gols_visitante=2,
        )
