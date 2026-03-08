from datetime import date
from unittest.mock import patch

import pytest
from django.core.management import call_command
from django.utils import timezone
from model_bakery import baker

from ..models import Competition, Match, Team

pytestmark = pytest.mark.django_db


@patch("requests.get")
def test_command_create_or_update_competitions_successfully(
    mock_get,
    mock_success_response,
    get_league_by_id_response,
):
    response_data = get_league_by_id_response
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
    mock_get, mock_success_response, football_api_empty_response
):
    response_data = football_api_empty_response
    mock_success_response.json.return_value = response_data
    mock_get.return_value = mock_success_response

    call_command("create_or_update_competitions", [0])

    mock_get.assert_called_once()

    assert not Competition.objects.exists()


@patch("requests.get")
def test_command_create_or_update_teams_for_competitions_successfully(
    mock_get,
    mock_success_response,
    get_teams_of_league_by_season_response,
):
    response_data = get_teams_of_league_by_season_response
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


@patch("core.management.commands.sync_matches_sfi.sleep")
@patch("core.management.commands.sync_matches_sfi.django_timezone")
@patch("requests.get")
def test_sync_matches_sfi_creates_not_started_match(
    mock_get,
    mock_tz,
    mock_sleep,
    mock_success_response,
    get_sfi_matches_by_day_future_response_page_1,
    get_sfi_matches_by_day_future_response_page_2,
    sfi_competition_id,
    sfi_home_team_id,
    sfi_away_team_id,
):
    """A NOT_STARTED match is created in the DB when it does not yet exist."""
    mock_tz.now.return_value.date.return_value = date(2026, 3, 3)
    mock_tz.timedelta = timezone.timedelta

    competition = baker.make("core.Competition", sfi_id=sfi_competition_id)
    home_team = baker.make("core.Team", sfi_id=sfi_home_team_id, competitions=[competition])
    away_team = baker.make("core.Team", sfi_id=sfi_away_team_id, competitions=[competition])

    # Two pages: page 1 has the NS match, page 2 has an untracked competition match.
    page_1 = mock_success_response
    page_1.json.return_value = get_sfi_matches_by_day_future_response_page_1

    page_2_response = type(mock_success_response)()
    page_2_response.status_code = 200
    page_2_response.raise_for_status = lambda: None
    page_2_response.json.return_value = get_sfi_matches_by_day_future_response_page_2

    mock_get.side_effect = [page_1, page_2_response]

    call_command("sync_matches_sfi", date=date(2026, 3, 3))

    assert Match.objects.filter(sfi_id="match-sfi-ns-001").exists()
    match = Match.objects.get(sfi_id="match-sfi-ns-001")
    assert match.status == Match.NOT_STARTED
    assert match.home_team == home_team
    assert match.away_team == away_team
    assert match.competition == competition
    assert match.home_goals is None
    assert match.away_goals is None


@patch("core.management.commands.sync_matches_sfi.django_timezone")
@patch("requests.get")
def test_sync_matches_sfi_updates_ended_match_when_exists(
    mock_get,
    mock_tz,
    mock_success_response,
    get_sfi_matches_by_day_past_response,
    sfi_competition_id,
    sfi_home_team_id,
    sfi_away_team_id,
):
    """An ENDED match that exists in the DB gets its goals updated."""
    mock_tz.now.return_value.date.return_value = date(2026, 3, 3)
    mock_tz.timedelta = timezone.timedelta

    competition = baker.make("core.Competition", sfi_id=sfi_competition_id)
    home_team = baker.make("core.Team", sfi_id=sfi_home_team_id, competitions=[competition])
    away_team = baker.make("core.Team", sfi_id=sfi_away_team_id, competitions=[competition])

    # Pre-create the match without goals (as if it was synced as NOT_STARTED earlier).
    existing_match = baker.make(
        "core.Match",
        sfi_id="match-sfi-ended-001",
        competition=competition,
        home_team=home_team,
        away_team=away_team,
        status=Match.NOT_STARTED,
        home_goals=None,
        away_goals=None,
    )

    mock_success_response.json.return_value = get_sfi_matches_by_day_past_response
    mock_get.return_value = mock_success_response

    call_command("sync_matches_sfi", date=date(2026, 2, 26))

    existing_match.refresh_from_db()

    assert existing_match.status == Match.FINSHED
    assert existing_match.home_goals == 2
    assert existing_match.away_goals == 1


@patch("core.management.commands.sync_matches_sfi.django_timezone")
@patch("requests.get")
def test_sync_matches_sfi_does_not_create_ended_match_when_not_in_db(
    mock_get,
    mock_tz,
    mock_success_response,
    get_sfi_matches_by_day_past_response,
    sfi_competition_id,
    sfi_home_team_id,
    sfi_away_team_id,
):
    """An ENDED match that is NOT yet in the DB must not be created."""
    mock_tz.now.return_value.date.return_value = date(2026, 3, 3)
    mock_tz.timedelta = timezone.timedelta

    competition = baker.make("core.Competition", sfi_id=sfi_competition_id)
    baker.make("core.Team", sfi_id=sfi_home_team_id, competitions=[competition])
    baker.make("core.Team", sfi_id=sfi_away_team_id, competitions=[competition])

    mock_success_response.json.return_value = get_sfi_matches_by_day_past_response
    mock_get.return_value = mock_success_response

    call_command("sync_matches_sfi", date=date(2026, 2, 26))

    assert not Match.objects.filter(sfi_id="match-sfi-ended-001").exists()


@patch("core.management.commands.sync_matches_sfi.django_timezone")
@patch("requests.get")
def test_sync_matches_sfi_skips_untracked_competition(
    mock_get,
    mock_tz,
    mock_success_response,
    get_sfi_matches_by_day_past_response,
):
    """Matches whose competition has no SFI ID are silently skipped."""
    mock_tz.now.return_value.date.return_value = date(2026, 3, 3)
    mock_tz.timedelta = timezone.timedelta

    # No competition with a matching sfi_id is registered.
    baker.make("core.Competition", sfi_id=None)

    mock_success_response.json.return_value = get_sfi_matches_by_day_past_response
    mock_get.return_value = mock_success_response

    call_command("sync_matches_sfi", date=date(2026, 2, 26))

    assert not Match.objects.exists()


@patch("core.management.commands.sync_matches_sfi.sleep")
@patch("core.management.commands.sync_matches_sfi.django_timezone")
@patch("requests.get")
def test_sync_matches_sfi_registers_unknown_teams_and_processes_match(
    mock_get,
    mock_tz,
    mock_sleep,
    mock_success_response,
    get_sfi_matches_by_day_future_response_page_1,
    get_sfi_matches_by_day_future_response_page_2,
    sfi_competition_id,
    sfi_home_team_id,
    sfi_away_team_id,
    capsys,
):
    """A match with unknown teams auto-registers them and proceeds with match sync."""
    mock_tz.now.return_value.date.return_value = date(2026, 3, 3)
    mock_tz.timedelta = timezone.timedelta

    # Competition exists but no teams are pre-registered.
    competition = baker.make("core.Competition", sfi_id=sfi_competition_id)

    page_1 = mock_success_response
    page_1.json.return_value = get_sfi_matches_by_day_future_response_page_1

    page_2_response = type(mock_success_response)()
    page_2_response.status_code = 200
    page_2_response.raise_for_status = lambda: None
    page_2_response.json.return_value = get_sfi_matches_by_day_future_response_page_2

    mock_get.side_effect = [page_1, page_2_response]

    call_command("sync_matches_sfi", date=date(2026, 3, 3))

    output = capsys.readouterr().out

    assert Match.objects.filter(sfi_id="match-sfi-ns-001").exists()

    home_team = Team.objects.get(sfi_id=sfi_home_team_id)
    away_team = Team.objects.get(sfi_id=sfi_away_team_id)
    assert competition.teams.filter(pk=home_team.pk).exists()
    assert competition.teams.filter(pk=away_team.pk).exists()

    assert f"(sfi_id={sfi_home_team_id})" in output
    assert f"(sfi_id={sfi_away_team_id})" in output
    assert "2 teams registered" in output


@patch("core.management.commands.sync_matches_sfi.sleep")
@patch("core.management.commands.sync_matches_sfi.django_timezone")
@patch("requests.get")
def test_sync_matches_sfi_paginated_future_date_calls_multiple_pages(
    mock_get,
    mock_tz,
    mock_sleep,
    mock_success_response,
    get_sfi_matches_by_day_future_response_page_1,
    get_sfi_matches_by_day_future_response_page_2,
    sfi_competition_id,
    sfi_home_team_id,
    sfi_away_team_id,
):
    """For a future date, requests.get is called once per page (two pages here)."""
    mock_tz.now.return_value.date.return_value = date(2026, 3, 3)
    mock_tz.timedelta = timezone.timedelta

    competition = baker.make("core.Competition", sfi_id=sfi_competition_id)
    baker.make("core.Team", sfi_id=sfi_home_team_id, competitions=[competition])
    baker.make("core.Team", sfi_id=sfi_away_team_id, competitions=[competition])

    page_1 = mock_success_response
    page_1.json.return_value = get_sfi_matches_by_day_future_response_page_1

    page_2_response = type(mock_success_response)()
    page_2_response.status_code = 200
    page_2_response.raise_for_status = lambda: None
    page_2_response.json.return_value = get_sfi_matches_by_day_future_response_page_2

    mock_get.side_effect = [page_1, page_2_response]

    call_command("sync_matches_sfi", date=date(2026, 3, 3))

    # One call per page (26 items / 25 per page = 2 pages).
    assert mock_get.call_count == 2


@patch("requests.get")
def test_sync_matches_sfi_with_no_competitions(mock_get):
    """When no competitions have an SFI ID, the command exits early without calling the API."""
    # Competition exists but has no sfi_id — should trigger the early-return path.
    baker.make("core.Competition", sfi_id=None)

    call_command("sync_matches_sfi")

    mock_get.assert_not_called()
