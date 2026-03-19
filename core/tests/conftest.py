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


@pytest.fixture
def sfi_competition_id():
    """SFI ID used for the tracked competition in SFI fixtures."""
    return "comp-sfi-001"


@pytest.fixture
def sfi_home_team_id():
    """SFI ID used for the home team in SFI fixtures."""
    return "team-home-sfi-001"


@pytest.fixture
def sfi_away_team_id():
    """SFI ID used for the away team in SFI fixtures."""
    return "team-away-sfi-001"


@pytest.fixture
def get_sfi_matches_by_day_past_response(sfi_competition_id, sfi_home_team_id, sfi_away_team_id):
    """Non-paginated SFI response (past date).

    Contains one ENDED match.  ``pagination`` is an empty list to match the
    actual API behaviour for past dates.
    """
    return {
        "status": 200,
        "errors": [],
        "pagination": [],
        "result": [
            {
                "id": "match-sfi-ended-001",
                "date": "2026-02-26 20:00:00",
                "status": "ENDED",
                "timer": "90:00",
                "championship": {
                    "id": sfi_competition_id,
                    "name": "Test League",
                    "s_name": "Test League 2026",
                },
                "teamA": {
                    "id": sfi_home_team_id,
                    "name": "Home FC",
                    "score": {"f": 2, "1h": 1, "2h": 2, "o": None, "p": None},
                },
                "teamB": {
                    "id": sfi_away_team_id,
                    "name": "Away FC",
                    "score": {"f": 1, "1h": 0, "2h": 1, "o": None, "p": None},
                },
            }
        ],
    }


@pytest.fixture
def get_sfi_matches_by_day_future_response_page_1(sfi_competition_id, sfi_home_team_id, sfi_away_team_id):
    """First page of a paginated SFI response (present/future date).

    Reports 26 total items across 2 pages of 25, so the command must request a
    second page.  Contains one NOT_STARTED match.
    """
    return {
        "status": 200,
        "errors": [],
        "pagination": [{"page": 1, "per_page": 25, "items": 26}],
        "result": [
            {
                "id": "match-sfi-ns-001",
                "date": "2026-03-03 20:00:00",
                "status": "NOT_STARTED",
                "timer": "00:00",
                "championship": {
                    "id": sfi_competition_id,
                    "name": "Test League",
                    "s_name": "Test League 2026",
                },
                "teamA": {
                    "id": sfi_home_team_id,
                    "name": "Home FC",
                    "score": {"f": 0, "1h": None, "2h": None, "o": None, "p": None},
                },
                "teamB": {
                    "id": sfi_away_team_id,
                    "name": "Away FC",
                    "score": {"f": 0, "1h": None, "2h": None, "o": None, "p": None},
                },
            }
        ],
    }


@pytest.fixture
def get_sfi_matches_by_day_future_response_page_2():
    """Second page of a paginated SFI response (present/future date).

    Contains one match for an untracked competition so that the command skips
    it, keeping assertions simple.
    """
    return {
        "status": 200,
        "errors": [],
        "pagination": [{"page": 2, "per_page": 25, "items": 26}],
        "result": [
            {
                "id": "match-sfi-other-001",
                "date": "2026-03-03 20:00:00",
                "status": "NOT_STARTED",
                "timer": "00:00",
                "championship": {
                    "id": "untracked-competition",
                    "name": "Other League",
                    "s_name": "Other League 2026",
                },
                "teamA": {
                    "id": "other-team-a",
                    "name": "Other A",
                    "score": {"f": 0, "1h": None, "2h": None, "o": None, "p": None},
                },
                "teamB": {
                    "id": "other-team-b",
                    "name": "Other B",
                    "score": {"f": 0, "1h": None, "2h": None, "o": None, "p": None},
                },
            }
        ],
    }
