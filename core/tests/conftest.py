from http import HTTPStatus
from unittest.mock import Mock

import pytest


@pytest.fixture
def mock_success_response():
    mock_response = Mock()
    mock_response.status_code = HTTPStatus.OK

    return mock_response


@pytest.fixture
def get_league_by_id_response():
    return {
        "response": [
            {
                "league": {
                    "id": 4,
                    "name": "Euro Championship",
                }
            }
        ]
    }


@pytest.fixture
def football_api_empty_response():
    return {"response": []}


@pytest.fixture
def get_teams_of_league_by_season_response():
    return {
        "response": [
            {
                "team": {
                    "id": 118,
                    "name": "Bahia",
                    "code": "BAH",
                    "country": "Brazil",
                    "founded": 1931,
                    "national": False,
                    "logo": "https://media.api-sports.io/football/teams/118.png",
                },
                "venue": {
                    "id": 216,
                    "name": "Arena Fonte Nova",
                    "address": "Rua Lions Club, Nazaré",
                    "city": "Salvador, Bahia",
                    "capacity": 56500,
                    "surface": "grass",
                    "image": "https://media.api-sports.io/football/venues/216.png",
                },
            },
            {
                "team": {
                    "id": 119,
                    "name": "Internacional",
                    "code": "INT",
                    "country": "Brazil",
                    "founded": 1909,
                    "national": False,
                    "logo": "https://media.api-sports.io/football/teams/119.png",
                },
                "venue": {
                    "id": 244,
                    "name": "Estádio José Pinheiro Borda",
                    "address": "Avenida Padre Cacique 891, Bairro Menino Deus",
                    "city": "Porto Alegre, Rio Grande do Sul",
                    "capacity": 50128,
                    "surface": "grass",
                    "image": "https://media.api-sports.io/football/venues/244.png",
                },
            },
        ],
    }


@pytest.fixture
def get_matches_of_league_by_season_and_date_period_response():
    return {
        "response": [
            {
                "fixture": {
                    "id": 1180355,
                    "referee": "Rodrigo José Pereira de Lima",
                    "timezone": "UTC",
                    "date": "2024-04-13T21:30:00+00:00",
                    "timestamp": 1713043800,
                    "periods": {
                        "first": 1713043800,
                        "second": 1713047400,
                    },
                    "status": {
                        "long": "Match Finished",
                        "short": "FT",
                        "elapsed": 90,
                    },
                },
                "teams": {
                    "home": {
                        "id": 119,
                        "name": "Internacional",
                        "logo": "https://media.api-sports.io/football/teams/119.png",
                        "winner": True,
                    },
                    "away": {
                        "id": 118,
                        "name": "Bahia",
                        "logo": "https://media.api-sports.io/football/teams/118.png",
                        "winner": False,
                    },
                },
                "goals": {
                    "home": 2,
                    "away": 1,
                },
            }
        ]
    }
