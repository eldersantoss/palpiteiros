from unittest.mock import patch

import pytest
from django.core.management import call_command
from django.utils import timezone
from model_bakery import baker

from ..models import Competition, Team

pytestmark = pytest.mark.django_db


@patch("requests.get")
def test_command_create_or_update_competitions_successfully(
    mock_get,
    mock_success_response,
    get_competition_by_id_and_season_response,
):
    response_data = get_competition_by_id_and_season_response
    league_id = response_data["response"][0]["league"]["id"]
    league_name = response_data["response"][0]["league"]["name"]

    mock_success_response.json.return_value = response_data
    mock_get.return_value = mock_success_response

    call_command("create_or_update_competitions", [league_id])

    mock_get.assert_called_once()

    competitions = Competition.objects.all()

    assert competitions.count() == 1
    assert competitions.first().data_source_id == league_id
    assert competitions.first().name == f"{league_name}"


@patch("requests.get")
def test_command_create_or_update_competitions_league_not_found(
    mock_get, mock_success_response, get_competition_by_id_and_season_empty_response
):
    response_data = get_competition_by_id_and_season_empty_response
    mock_success_response.json.return_value = response_data
    mock_get.return_value = mock_success_response

    call_command("create_or_update_competitions", [0])

    mock_get.assert_called_once()

    assert not Competition.objects.exists()


@patch("requests.get")
def test_command_create_or_update_teams_for_competitions_successfully(
    mock_get,
    mock_success_response,
    get_teams_by_league_and_season_response,
):
    response_data = get_teams_by_league_and_season_response
    mock_success_response.json.return_value = response_data
    mock_get.return_value = mock_success_response
    competition = baker.make("core.Competition")

    call_command(
        "create_or_update_teams_for_competitions",
        timezone.now().year,
        [competition.data_source_id],
    )

    mock_get.assert_called_once()

    teams = Team.objects.all()

    assert teams.count() == len(response_data["response"])
    assert all([team.competitions.filter(data_source_id=competition.data_source_id).exists() for team in teams])
