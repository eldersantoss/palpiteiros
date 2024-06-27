from unittest.mock import patch

import pytest
from django.utils import timezone
from model_bakery import baker

from ..models import Competition

pytestmark = pytest.mark.django_db


@patch("requests.get")
def test_create_or_update(mock_get, mock_success_response, get_competition_by_id_and_season_response):
    response_data = get_competition_by_id_and_season_response
    league_id = response_data["response"][0]["league"]["id"]
    league_name = response_data["response"][0]["league"]["name"]
    season = 2024

    mock_success_response.json.return_value = response_data
    mock_get.return_value = mock_success_response

    Competition.create_or_update(season, league_id)

    mock_get.assert_called_once()

    competitions = Competition.objects.all()

    assert competitions.count() == 1
    assert competitions.first().name == f"{league_name}"


@patch("requests.get")
def test_get_teams(mock_get, mock_success_response, get_teams_by_league_and_season_response):
    response_data = get_teams_by_league_and_season_response

    mock_success_response.json.return_value = response_data
    mock_get.return_value = mock_success_response

    competition = baker.make("core.Competition")

    competition.get_teams()

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

    created, updated = competition.create_and_update_matches()

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

    created, updated = competition.create_and_update_matches()

    mock_get.assert_called_once()

    assert competition.matches.count() == len(response_data["response"])
    assert len(created) == 0
    assert len(updated) == 1
