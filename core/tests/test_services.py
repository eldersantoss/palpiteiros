from datetime import date
from unittest.mock import Mock, patch

import pytest
from django.conf import settings

from core.services.football import FootballApi

pytestmark = pytest.mark.django_db


@patch("requests.get")
def test_fetch_data_success(mock_get: Mock, mock_success_response):
    mock_success_response.json.return_value = {"response": "data"}
    mock_get.return_value = mock_success_response

    resource = "/test_resource"
    params = {"param1": "value1"}

    response = FootballApi._fetch_data(resource, params)

    mock_get.assert_called_once_with(
        FootballApi._API_URL + resource, headers=FootballApi._DEFAULT_HEADERS, params=params
    )
    assert response is not None
    assert response.status_code == 200
    assert response.json() == {"response": "data"}


@patch("requests.get")
def test_fetch_data_failure(mock_get):
    mock_get.side_effect = Exception()

    resource = "/test_resource"
    params = {"param1": "value1"}

    response = FootballApi._fetch_data(resource, params)

    mock_get.assert_called_once_with(
        FootballApi._API_URL + resource, headers=FootballApi._DEFAULT_HEADERS, params=params
    )
    assert response is None


@patch("core.services.football.FootballApi._fetch_data")
def test_football_api_get_league_by_id_successfully(
    mock_fetch_data: Mock,
    mock_success_response,
    get_league_by_id_response,
):
    mock_success_response.json.return_value = get_league_by_id_response
    mock_fetch_data.return_value = mock_success_response

    response = FootballApi.get_league_by_id(0)

    mock_fetch_data.assert_called_once_with("/leagues", {"id": 0})
    assert response == mock_success_response.json()["response"][0]


@patch("core.services.football.FootballApi._fetch_data")
def test_football_api_get_league_by_id_not_found(
    mock_fetch_data: Mock,
    mock_success_response,
    football_api_empty_response,
):
    mock_success_response.json.return_value = football_api_empty_response
    mock_fetch_data.return_value = mock_success_response

    response = FootballApi.get_league_by_id(0)

    mock_fetch_data.assert_called_once_with("/leagues", {"id": 0})
    assert response is None


@patch("core.services.football.FootballApi._fetch_data")
def test_football_api_get_league_by_id_failure(mock_fetch_data: Mock):
    mock_fetch_data.return_value = None

    response = FootballApi.get_league_by_id(0)

    mock_fetch_data.assert_called_once_with("/leagues", {"id": 0})
    assert response is None


@patch("core.services.football.FootballApi._fetch_data")
def test_football_api_get_teams_of_league_by_season_successfully(
    mock_fetch_data: Mock,
    mock_success_response,
    get_teams_of_league_by_season_response,
):
    mock_success_response.json.return_value = get_teams_of_league_by_season_response
    mock_fetch_data.return_value = mock_success_response
    league_id = 71
    season = 2024

    response = FootballApi.get_teams_of_league_by_season(league_id, season)

    mock_fetch_data.assert_called_once_with("/teams", {"league": league_id, "season": season})
    assert response == get_teams_of_league_by_season_response["response"]


@patch("core.services.football.FootballApi._fetch_data")
def test_football_api_get_teams_of_league_by_season_not_found(
    mock_fetch_data: Mock,
    mock_success_response,
    football_api_empty_response,
):
    mock_success_response.json.return_value = football_api_empty_response
    mock_fetch_data.return_value = mock_success_response
    league_id = 71
    season = 2024

    response = FootballApi.get_teams_of_league_by_season(league_id, season)

    mock_fetch_data.assert_called_once_with("/teams", {"league": league_id, "season": season})
    assert response == []


@patch("core.services.football.FootballApi._fetch_data")
def test_football_api_get_matches_of_league_by_season_and_date_period_successfully(
    mock_fetch_data: Mock,
    mock_success_response,
    get_matches_of_league_by_season_and_date_period_response,
):
    mock_success_response.json.return_value = get_matches_of_league_by_season_and_date_period_response
    mock_fetch_data.return_value = mock_success_response
    league_id = 71
    season = 2024
    start_date = date(2024, 5, 23)
    end_date = date(2024, 5, 23)

    response = FootballApi.get_matches_of_league_by_season_and_date_period(
        league_id,
        season,
        start_date,
        end_date,
    )

    mock_fetch_data.assert_called_once_with(
        "/fixtures",
        {
            "timezone": settings.TIME_ZONE,
            "league": league_id,
            "season": season,
            "from": str(start_date),
            "to": str(end_date),
        },
    )
    assert response == get_matches_of_league_by_season_and_date_period_response["response"]


@patch("core.services.football.FootballApi._fetch_data")
def test_football_api_get_matches_of_league_by_season_and_date_period_not_found(
    mock_fetch_data: Mock,
    mock_success_response,
    football_api_empty_response,
):
    mock_success_response.json.return_value = football_api_empty_response
    mock_fetch_data.return_value = mock_success_response
    league_id = 71
    season = 2024
    start_date = date(2024, 5, 23)
    end_date = date(2024, 5, 23)

    response = FootballApi.get_matches_of_league_by_season_and_date_period(
        league_id,
        season,
        start_date,
        end_date,
    )

    mock_fetch_data.assert_called_once_with(
        "/fixtures",
        {
            "timezone": settings.TIME_ZONE,
            "league": league_id,
            "season": season,
            "from": str(start_date),
            "to": str(end_date),
        },
    )
    assert response == []
