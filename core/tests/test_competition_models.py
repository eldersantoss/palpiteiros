from unittest.mock import patch

import pytest
from django.utils import timezone
from model_bakery import baker

pytestmark = pytest.mark.django_db


@patch("requests.get")
def test_get_teams(mock_get, mock_success_response, get_teams_by_league_and_season_response):
    response_data = get_teams_by_league_and_season_response

    mock_success_response.json.return_value = response_data
    mock_get.return_value = mock_success_response

    competition = baker.make("core.Competition")

    competition.get_teams(timezone.now().year)

    mock_get.assert_called_once()

    assert competition.teams.count() == len(response_data["response"])


@patch("requests.get")
def test_create_matches(mock_get, mock_success_response, get_matches_by_league_and_season_response):
    response_data = get_matches_by_league_and_season_response

    mock_success_response.json.return_value = response_data
    mock_get.return_value = mock_success_response

    competition = baker.make("core.Competition")
    home_team = baker.make("core.Team", data_source_id=response_data["response"][0]["teams"]["home"]["id"])
    away_team = baker.make("core.Team", data_source_id=response_data["response"][0]["teams"]["away"]["id"])
    competition.teams.set([home_team, away_team])

    # TODO: remover parâmetros hardcoded
    created, updated = competition.create_and_update_matches(2024, 3, 3)

    mock_get.assert_called_once()

    assert competition.matches.count() == len(response_data["response"])
    assert len(created) == 1
    assert len(updated) == 0


@patch("requests.get")
def test_update_matches(mock_get, mock_success_response, get_matches_by_league_and_season_response):
    response_data = get_matches_by_league_and_season_response

    mock_success_response.json.return_value = response_data
    mock_get.return_value = mock_success_response

    competition = baker.make("core.Competition")
    home_team = baker.make("core.Team", data_source_id=response_data["response"][0]["teams"]["home"]["id"])
    away_team = baker.make("core.Team", data_source_id=response_data["response"][0]["teams"]["away"]["id"])
    competition.teams.set([home_team, away_team])

    data_source_id = response_data["response"][0]["fixture"]["id"]
    date_time = timezone.datetime.fromisoformat(response_data["response"][0]["fixture"]["date"])
    status = response_data["response"][0]["fixture"]["status"]["short"]
    baker.make(
        "core.Match",
        data_source_id=data_source_id,
        competition=competition,
        status=status,
        home_team=home_team,
        away_team=away_team,
        date_time=date_time,
    )

    # TODO: remover parâmetros hardcoded
    created, updated = competition.create_and_update_matches(2024, 3, 3)

    mock_get.assert_called_once()

    assert competition.matches.count() == len(response_data["response"])
    assert len(created) == 0
    assert len(updated) == 1
