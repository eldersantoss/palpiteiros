from unittest.mock import patch

import pytest

from core.services.football import FootballApiService

pytestmark = pytest.mark.django_db


@patch("requests.get")
def test_football_api_service_get_league_by_id_successfully(
    mock_get,
    mock_success_response,
    get_competition_by_id_and_season_response,
):
    response_data = get_competition_by_id_and_season_response
    league_id = response_data["response"][0]["league"]["id"]
    mock_success_response.json.return_value = response_data
    mock_get.return_value = mock_success_response

    league_data = FootballApiService.get_league_by_id(league_id)

    mock_get.assert_called_once()
    assert league_data == response_data["response"][0]


@patch("requests.get")
def test_football_api_service_get_league_by_id_league_not_found(
    mock_get,
    mock_success_response,
    get_competition_by_id_and_season_empty_response,
):
    response_data = get_competition_by_id_and_season_empty_response
    mock_success_response.json.return_value = response_data
    mock_get.return_value = mock_success_response

    league_data = FootballApiService.get_league_by_id(0)

    mock_get.assert_called_once()
    assert league_data is None
