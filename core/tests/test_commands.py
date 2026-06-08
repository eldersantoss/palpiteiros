import json
from datetime import date, datetime, timezone as dt_timezone
from unittest.mock import patch

import pytest
import requests
from django.core.management import call_command
from django.utils import timezone
from model_bakery import baker

from ..models import Competition, Match, RankingEntry, Team

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
    competition = baker.make("core.Competition", data_source_id=71)

    call_command(
        "create_or_update_teams_for_competitions",
        timezone.now().year,
        [competition.data_source_id],
    )

    mock_get.assert_called_once()

    teams = Team.objects.all()

    assert teams.count() == len(response_data["response"])
    assert all([team.competitions.filter(data_source_id=competition.data_source_id).exists() for team in teams])


@patch("core.management.commands.sync_sfi_matches.sleep")
@patch("core.management.commands.sync_sfi_matches.django_timezone")
@patch("requests.get")
def test_sync_sfi_matches_creates_not_started_match(
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

    competition = baker.make("core.Competition", sfi_id=sfi_competition_id, in_progress=True)
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

    call_command("sync_sfi_matches", date=date(2026, 3, 3))

    assert Match.objects.filter(sfi_id="match-sfi-ns-001").exists()
    match = Match.objects.get(sfi_id="match-sfi-ns-001")
    assert match.status == Match.NOT_STARTED
    assert match.home_team == home_team
    assert match.away_team == away_team
    assert match.competition == competition
    assert match.home_goals is None
    assert match.away_goals is None


@patch("core.management.commands.sync_sfi_matches.django_timezone")
@patch("requests.get")
def test_sync_sfi_matches_updates_ended_match_when_exists(
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

    competition = baker.make("core.Competition", sfi_id=sfi_competition_id, in_progress=True)
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

    call_command("sync_sfi_matches", date=date(2026, 2, 26))

    existing_match.refresh_from_db()

    assert existing_match.status == Match.FINSHED
    assert existing_match.home_goals == 2
    assert existing_match.away_goals == 1
    assert existing_match.home_yellow_cards == 2
    assert existing_match.away_yellow_cards == 3
    assert existing_match.home_red_cards == 1
    assert existing_match.away_red_cards == 0


@patch("core.management.commands.sync_sfi_matches.django_timezone")
@patch("requests.get")
def test_sync_sfi_matches_updates_ranking_entries_for_ended_match(
    mock_get,
    mock_tz,
    mock_success_response,
    get_sfi_matches_by_day_past_response,
    sfi_competition_id,
    sfi_home_team_id,
    sfi_away_team_id,
):
    """Ended match sync consolidates guesses and updates period rankings."""
    mock_tz.now.return_value.date.return_value = date(2026, 3, 3)
    mock_tz.timedelta = timezone.timedelta

    competition = baker.make("core.Competition", sfi_id=sfi_competition_id, in_progress=True)
    home_team = baker.make("core.Team", sfi_id=sfi_home_team_id, competitions=[competition])
    away_team = baker.make("core.Team", sfi_id=sfi_away_team_id, competitions=[competition])
    guesser = baker.make("core.Guesser")
    pool = baker.make("core.GuessPool", owner=guesser, competitions=[competition])

    existing_match = baker.make(
        "core.Match",
        sfi_id="match-sfi-ended-001",
        competition=competition,
        home_team=home_team,
        away_team=away_team,
        status=Match.NOT_STARTED,
        home_goals=None,
        away_goals=None,
        date_time=timezone.make_aware(datetime(2026, 2, 26, 20, 0, 0)),
    )

    guess = baker.make(
        "core.Guess",
        guesser=guesser,
        match=existing_match,
        home_goals=2,
        away_goals=1,
        score=0,
        consolidated=False,
    )
    pool.guesses.add(guess)

    mock_success_response.json.return_value = get_sfi_matches_by_day_past_response
    mock_get.return_value = mock_success_response

    call_command("sync_sfi_matches", date=date(2026, 2, 26))

    pool.refresh_from_db()
    guess.refresh_from_db()

    assert guess.consolidated is True
    assert guess.score == 10
    assert pool.updated_matches is True

    local_match_date = timezone.localtime(existing_match.date_time)
    expected_periods = [
        (0, 0, 0),
        (local_match_date.year, 0, 0),
        (local_match_date.year, local_match_date.month, 0),
        (local_match_date.year, 0, local_match_date.isocalendar().week),
    ]
    for year, month, week in expected_periods:
        assert RankingEntry.objects.filter(
            pool=pool,
            guesser=guesser,
            year=year,
            month=month,
            week=week,
            score=10,
        ).exists()


@patch("core.management.commands.sync_sfi_matches.django_timezone")
@patch("requests.get")
def test_sync_sfi_matches_does_not_create_ended_match_when_not_in_db(
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

    competition = baker.make("core.Competition", sfi_id=sfi_competition_id, in_progress=True)
    baker.make("core.Team", sfi_id=sfi_home_team_id, competitions=[competition])
    baker.make("core.Team", sfi_id=sfi_away_team_id, competitions=[competition])

    mock_success_response.json.return_value = get_sfi_matches_by_day_past_response
    mock_get.return_value = mock_success_response

    call_command("sync_sfi_matches", date=date(2026, 2, 26))

    assert not Match.objects.filter(sfi_id="match-sfi-ended-001").exists()


@patch("core.management.commands.sync_sfi_matches.django_timezone")
@patch("requests.get")
def test_sync_sfi_matches_skips_untracked_competition(
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

    call_command("sync_sfi_matches", date=date(2026, 2, 26))

    assert not Match.objects.exists()


@patch("core.management.commands.sync_sfi_matches.sleep")
@patch("core.management.commands.sync_sfi_matches.django_timezone")
@patch("requests.get")
def test_sync_sfi_matches_registers_unknown_teams_and_processes_match(
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
    competition = baker.make("core.Competition", sfi_id=sfi_competition_id, in_progress=True)

    page_1 = mock_success_response
    page_1.json.return_value = get_sfi_matches_by_day_future_response_page_1

    page_2_response = type(mock_success_response)()
    page_2_response.status_code = 200
    page_2_response.raise_for_status = lambda: None
    page_2_response.json.return_value = get_sfi_matches_by_day_future_response_page_2

    mock_get.side_effect = [page_1, page_2_response]

    call_command("sync_sfi_matches", date=date(2026, 3, 3))

    output = capsys.readouterr().out

    assert Match.objects.filter(sfi_id="match-sfi-ns-001").exists()

    home_team = Team.objects.get(sfi_id=sfi_home_team_id)
    away_team = Team.objects.get(sfi_id=sfi_away_team_id)
    assert competition.teams.filter(pk=home_team.pk).exists()
    assert competition.teams.filter(pk=away_team.pk).exists()

    assert f"(sfi_id={sfi_home_team_id})" in output
    assert f"(sfi_id={sfi_away_team_id})" in output
    assert "2 teams registered" in output


@patch("core.management.commands.sync_sfi_matches.sleep")
@patch("core.management.commands.sync_sfi_matches.django_timezone")
@patch("requests.get")
def test_sync_sfi_matches_paginated_future_date_calls_multiple_pages(
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

    competition = baker.make("core.Competition", sfi_id=sfi_competition_id, in_progress=True)
    baker.make("core.Team", sfi_id=sfi_home_team_id, competitions=[competition])
    baker.make("core.Team", sfi_id=sfi_away_team_id, competitions=[competition])

    page_1 = mock_success_response
    page_1.json.return_value = get_sfi_matches_by_day_future_response_page_1

    page_2_response = type(mock_success_response)()
    page_2_response.status_code = 200
    page_2_response.raise_for_status = lambda: None
    page_2_response.json.return_value = get_sfi_matches_by_day_future_response_page_2

    mock_get.side_effect = [page_1, page_2_response]

    call_command("sync_sfi_matches", date=date(2026, 3, 3))

    # One call per page (26 items / 25 per page = 2 pages).
    assert mock_get.call_count == 2


@patch("requests.get")
def test_sync_sfi_matches_with_no_competitions(mock_get):
    """When no competitions have an SFI ID, the command exits early without calling the API."""
    # Competition exists but has no sfi_id — should trigger the early-return path.
    baker.make("core.Competition", sfi_id=None)

    call_command("sync_sfi_matches")

    mock_get.assert_not_called()


@patch("core.management.commands.sync_sfi_matches.django_timezone")
@patch("requests.get")
def test_sync_sfi_matches_skips_competition_not_in_progress(
    mock_get,
    mock_tz,
    mock_success_response,
    get_sfi_matches_by_day_past_response,
    sfi_competition_id,
    sfi_home_team_id,
    sfi_away_team_id,
):
    """A competition with in_progress=False is excluded from the sync — no API call is made."""
    mock_tz.now.return_value.date.return_value = date(2026, 3, 3)
    mock_tz.timedelta = timezone.timedelta

    competition = baker.make("core.Competition", sfi_id=sfi_competition_id, in_progress=False)
    baker.make("core.Team", sfi_id=sfi_home_team_id, competitions=[competition])
    baker.make("core.Team", sfi_id=sfi_away_team_id, competitions=[competition])

    call_command("sync_sfi_matches", date=date(2026, 2, 26))

    mock_get.assert_not_called()
    assert not Match.objects.exists()


@patch("core.management.commands.sync_sfi_matches.django_timezone")
@patch("requests.get")
def test_sync_sfi_matches_updates_card_counts_for_ended_match(
    mock_get,
    mock_tz,
    mock_success_response,
    get_sfi_matches_by_day_past_response,
    sfi_competition_id,
    sfi_home_team_id,
    sfi_away_team_id,
):
    """Card counts are updated even when goals did not change."""
    mock_tz.now.return_value.date.return_value = date(2026, 3, 3)
    mock_tz.timedelta = timezone.timedelta

    competition = baker.make("core.Competition", sfi_id=sfi_competition_id, in_progress=True)
    home_team = baker.make("core.Team", sfi_id=sfi_home_team_id, competitions=[competition])
    away_team = baker.make("core.Team", sfi_id=sfi_away_team_id, competitions=[competition])

    existing_match = baker.make(
        "core.Match",
        sfi_id="match-sfi-ended-001",
        competition=competition,
        home_team=home_team,
        away_team=away_team,
        status=Match.FINSHED,
        home_goals=2,
        away_goals=1,
        home_yellow_cards=None,
        away_yellow_cards=None,
        home_red_cards=None,
        away_red_cards=None,
    )

    mock_success_response.json.return_value = get_sfi_matches_by_day_past_response
    mock_get.return_value = mock_success_response

    call_command("sync_sfi_matches", date=date(2026, 2, 26))

    existing_match.refresh_from_db()
    assert existing_match.home_yellow_cards == 2
    assert existing_match.away_yellow_cards == 3
    assert existing_match.home_red_cards == 1
    assert existing_match.away_red_cards == 0


@patch("core.management.commands.sync_sfi_matches.django_timezone")
@patch("requests.get")
def test_sync_sfi_matches_updates_date_time_for_ended_match(
    mock_get,
    mock_tz,
    mock_success_response,
    get_sfi_matches_by_day_past_response,
    sfi_competition_id,
    sfi_home_team_id,
    sfi_away_team_id,
):
    """An ENDED match gets its date_time updated when the API returns a different value."""
    mock_tz.now.return_value.date.return_value = date(2026, 3, 3)
    mock_tz.timedelta = timezone.timedelta

    competition = baker.make("core.Competition", sfi_id=sfi_competition_id, in_progress=True)
    home_team = baker.make("core.Team", sfi_id=sfi_home_team_id, competitions=[competition])
    away_team = baker.make("core.Team", sfi_id=sfi_away_team_id, competitions=[competition])

    old_date_time = datetime(2026, 2, 25, 18, 0, 0, tzinfo=dt_timezone.utc)
    existing_match = baker.make(
        "core.Match",
        sfi_id="match-sfi-ended-001",
        competition=competition,
        home_team=home_team,
        away_team=away_team,
        status=Match.NOT_STARTED,
        home_goals=None,
        away_goals=None,
        date_time=old_date_time,
    )

    mock_success_response.json.return_value = get_sfi_matches_by_day_past_response
    mock_get.return_value = mock_success_response

    call_command("sync_sfi_matches", date=date(2026, 2, 26))

    existing_match.refresh_from_db()
    assert existing_match.date_time == datetime(2026, 2, 26, 20, 0, 0, tzinfo=dt_timezone.utc)


@patch("core.management.commands.sync_sfi_matches.django_timezone")
@patch("requests.get")
def test_sync_sfi_matches_handles_null_card_stats(
    mock_get,
    mock_tz,
    mock_success_response,
    sfi_competition_id,
    sfi_home_team_id,
    sfi_away_team_id,
):
    """When fouls stats are null the card fields are stored as None, not 0."""
    mock_tz.now.return_value.date.return_value = date(2026, 3, 3)
    mock_tz.timedelta = timezone.timedelta

    competition = baker.make("core.Competition", sfi_id=sfi_competition_id, in_progress=True)
    home_team = baker.make("core.Team", sfi_id=sfi_home_team_id, competitions=[competition])
    away_team = baker.make("core.Team", sfi_id=sfi_away_team_id, competitions=[competition])

    baker.make(
        "core.Match",
        sfi_id="match-sfi-null-cards",
        competition=competition,
        home_team=home_team,
        away_team=away_team,
        status=Match.NOT_STARTED,
        home_goals=None,
        away_goals=None,
    )

    null_cards_response = {
        "status": 200,
        "errors": [],
        "pagination": [],
        "result": [
            {
                "id": "match-sfi-null-cards",
                "date": "2026-02-26 20:00:00",
                "status": "ENDED",
                "timer": "90:00",
                "championship": {"id": sfi_competition_id, "name": "Test League", "s_name": None},
                "teamA": {
                    "id": sfi_home_team_id,
                    "name": "Home FC",
                    "score": {"f": 1, "1h": 1, "2h": 1, "o": None, "p": None},
                    "stats": {
                        "possession": None,
                        "attacks": {"n": None, "d": None, "o_s": None},
                        "shoots": {"t": None, "off": None, "on": None, "g_a": None},
                        "penalties": None,
                        "corners": {"t": None, "f": None, "h": None},
                        "fouls": {"t": None, "y_c": None, "y_t_r_c": None, "r_c": None},
                        "substitutions": None,
                        "throwins": None,
                        "injuries": None,
                        "dominance_avg_2_5": None,
                        "xG": {"kickoff": None, "live": None},
                    },
                },
                "teamB": {
                    "id": sfi_away_team_id,
                    "name": "Away FC",
                    "score": {"f": 0, "1h": 0, "2h": 0, "o": None, "p": None},
                    "stats": {
                        "possession": None,
                        "attacks": {"n": None, "d": None, "o_s": None},
                        "shoots": {"t": None, "off": None, "on": None, "g_a": None},
                        "penalties": None,
                        "corners": {"t": None, "f": None, "h": None},
                        "fouls": {"t": None, "y_c": None, "y_t_r_c": None, "r_c": None},
                        "substitutions": None,
                        "throwins": None,
                        "injuries": None,
                        "dominance_avg_2_5": None,
                        "xG": {"kickoff": None, "live": None},
                    },
                },
            }
        ],
    }

    mock_success_response.json.return_value = null_cards_response
    mock_get.return_value = mock_success_response

    call_command("sync_sfi_matches", date=date(2026, 2, 26))

    match = Match.objects.get(sfi_id="match-sfi-null-cards")
    assert match.home_yellow_cards is None
    assert match.away_yellow_cards is None
    assert match.home_red_cards is None
    assert match.away_red_cards is None


@patch("core.management.commands.create_and_update_matches.sleep")
@patch("core.management.commands.create_and_update_matches.FootballApi.get_matches_of_league_by_season_and_date_period")
def test_create_and_update_matches_updates_ranking_entries_for_finished_match(
    mock_get_matches,
    mock_sleep,
    get_matches_of_league_by_season_and_date_period_response,
):
    """Legacy command updates rankings when a match result is synchronized."""
    competition = baker.make("core.Competition", data_source_id=4, in_progress=True, current_season=2024)
    home_team = baker.make("core.Team", data_source_id=119, competitions=[competition])
    away_team = baker.make("core.Team", data_source_id=118, competitions=[competition])
    guesser = baker.make("core.Guesser")
    pool = baker.make("core.GuessPool", owner=guesser, competitions=[competition])

    existing_match = baker.make(
        "core.Match",
        data_source_id=1180355,
        competition=competition,
        home_team=home_team,
        away_team=away_team,
        status=Match.NOT_STARTED,
        home_goals=None,
        away_goals=None,
        date_time=timezone.make_aware(datetime(2024, 4, 13, 21, 30, 0)),
    )
    guess = baker.make(
        "core.Guess",
        guesser=guesser,
        match=existing_match,
        home_goals=2,
        away_goals=1,
        score=0,
        consolidated=False,
    )
    pool.guesses.add(guess)

    mock_get_matches.return_value = get_matches_of_league_by_season_and_date_period_response["response"]

    call_command(
        "create_and_update_matches",
        start_date=date(2024, 4, 13),
        end_date=date(2024, 4, 13),
    )

    pool.refresh_from_db()
    guess.refresh_from_db()

    assert guess.consolidated is True
    assert guess.score == 10
    assert pool.updated_matches is True

    local_match_date = timezone.localtime(existing_match.date_time)
    assert RankingEntry.objects.filter(
        pool=pool,
        guesser=guesser,
        year=local_match_date.year,
        month=0,
        week=0,
        score=10,
    ).exists()


@patch("core.management.commands.get_teams_of_championships_sfi.sleep")
@patch("requests.get")
def test_get_teams_of_championships_sfi_creates_output_with_custom_paths(
    mock_get,
    mock_sleep,
    mock_success_response,
    tmp_path,
):
    """Command reads custom input/output paths and persists teams from SFIService responses."""
    input_file = tmp_path / "input.json"
    output_file = tmp_path / "output.json"

    input_file.write_text(
        json.dumps(
            [
                {"id": "champ-1", "name": "League 1"},
                {"id": "champ-2", "name": "League 2"},
            ]
        ),
        encoding="utf-8",
    )

    first_response = mock_success_response
    first_response.json.return_value = {
        "status": 200,
        "errors": [],
        "pagination": [],
        "result": [
            {
                "id": "champ-1",
                "name": "League 1",
                "country": "Brazil",
                "has_image": False,
                "important": True,
                "seasons": [
                    {
                        "id": "season-1",
                        "name": "2026",
                        "from": "2026-01-01",
                        "to": "2026-12-31",
                        "groups": [
                            {
                                "name": "A",
                                "table": [
                                    {
                                        "team": {"id": "team-1", "name": "Team 1"},
                                        "position": 1,
                                        "win": 1,
                                        "draw": 0,
                                        "loss": 0,
                                        "points": 3,
                                        "goals_scored": 2,
                                        "goals_conceded": 0,
                                        "note": None,
                                    }
                                ],
                            }
                        ],
                    }
                ],
            }
        ],
    }

    second_response = type(mock_success_response)()
    second_response.status_code = 200
    second_response.raise_for_status = lambda: None
    second_response.json.return_value = {
        "status": 200,
        "errors": [],
        "pagination": [],
        "result": [
            {
                "id": "champ-2",
                "name": "League 2",
                "country": "Brazil",
                "has_image": False,
                "important": True,
                "seasons": [
                    {
                        "id": "season-2",
                        "name": "2026",
                        "from": "2026-01-01",
                        "to": "2026-12-31",
                        "groups": [
                            {
                                "name": "A",
                                "table": [
                                    {
                                        "team": {"id": "team-2", "name": "Team 2"},
                                        "position": 1,
                                        "win": 1,
                                        "draw": 0,
                                        "loss": 0,
                                        "points": 3,
                                        "goals_scored": 1,
                                        "goals_conceded": 0,
                                        "note": None,
                                    }
                                ],
                            }
                        ],
                    }
                ],
            }
        ],
    }

    mock_get.side_effect = [first_response, second_response]

    call_command(
        "get_teams_of_championships_sfi",
        "--input-file",
        str(input_file),
        "--output-file",
        str(output_file),
        "--sleep-seconds",
        "0",
    )

    saved_data = json.loads(output_file.read_text(encoding="utf-8"))
    assert len(saved_data) == 2
    assert saved_data[0]["id"] == "champ-1"
    assert saved_data[0]["teams"] == [{"id": "team-1", "name": "Team 1"}]
    assert saved_data[1]["id"] == "champ-2"
    assert saved_data[1]["teams"] == [{"id": "team-2", "name": "Team 2"}]


@patch("core.management.commands.get_teams_of_championships_sfi.sleep")
@patch("requests.get")
def test_get_teams_of_championships_sfi_overwrites_existing_entry_by_id(
    mock_get,
    mock_sleep,
    mock_success_response,
    tmp_path,
):
    """Existing output entry with same championship ID is replaced instead of duplicated."""
    input_file = tmp_path / "input.json"
    output_file = tmp_path / "output.json"

    input_file.write_text(json.dumps([{"id": "champ-1", "name": "League Updated"}]), encoding="utf-8")
    output_file.write_text(
        json.dumps([{"id": "champ-1", "name": "Old League", "teams": [{"id": "old", "name": "Old"}]}]),
        encoding="utf-8",
    )

    mock_success_response.json.return_value = {
        "status": 200,
        "errors": [],
        "pagination": [],
        "result": [
            {
                "id": "champ-1",
                "name": "League Updated",
                "country": "Brazil",
                "has_image": False,
                "important": True,
                "seasons": [
                    {
                        "id": "season-1",
                        "name": "2026",
                        "from": "2026-01-01",
                        "to": "2026-12-31",
                        "groups": [
                            {
                                "name": "A",
                                "table": [
                                    {
                                        "team": {"id": "team-new", "name": "New Team"},
                                        "position": 1,
                                        "win": 1,
                                        "draw": 0,
                                        "loss": 0,
                                        "points": 3,
                                        "goals_scored": 1,
                                        "goals_conceded": 0,
                                        "note": None,
                                    }
                                ],
                            }
                        ],
                    }
                ],
            }
        ],
    }
    mock_get.return_value = mock_success_response

    call_command(
        "get_teams_of_championships_sfi",
        "--input-file",
        str(input_file),
        "--output-file",
        str(output_file),
        "--sleep-seconds",
        "0",
    )

    saved_data = json.loads(output_file.read_text(encoding="utf-8"))
    assert len(saved_data) == 1
    assert saved_data[0]["id"] == "champ-1"
    assert saved_data[0]["name"] == "League Updated"
    assert saved_data[0]["teams"] == [{"id": "team-new", "name": "New Team"}]


@patch("core.management.commands.get_teams_of_championships_sfi.sleep")
@patch("requests.get")
def test_get_teams_of_championships_sfi_continues_after_request_failure(
    mock_get,
    mock_sleep,
    mock_success_response,
    tmp_path,
):
    """When one championship fails, command logs and continues processing the next one."""
    input_file = tmp_path / "input.json"
    output_file = tmp_path / "output.json"

    input_file.write_text(
        json.dumps(
            [
                {"id": "champ-fail", "name": "Fail League"},
                {"id": "champ-ok", "name": "OK League"},
            ]
        ),
        encoding="utf-8",
    )

    mock_success_response.json.return_value = {
        "status": 200,
        "errors": [],
        "pagination": [],
        "result": [
            {
                "id": "champ-ok",
                "name": "OK League",
                "country": "Brazil",
                "has_image": False,
                "important": True,
                "seasons": [
                    {
                        "id": "season-2025",
                        "name": "2025",
                        "from": "2025-01-01",
                        "to": "2025-12-31",
                        "groups": [
                            {
                                "name": "A",
                                "table": [
                                    {
                                        "team": {"id": "team-2025", "name": "Team 2025"},
                                        "position": 1,
                                        "win": 1,
                                        "draw": 0,
                                        "loss": 0,
                                        "points": 3,
                                        "goals_scored": 1,
                                        "goals_conceded": 0,
                                        "note": None,
                                    }
                                ],
                            }
                        ],
                    }
                ],
            }
        ],
    }

    mock_get.side_effect = [requests.RequestException("boom"), mock_success_response]

    call_command(
        "get_teams_of_championships_sfi",
        "--input-file",
        str(input_file),
        "--output-file",
        str(output_file),
        "--year",
        "2025",
        "--sleep-seconds",
        "0",
    )

    saved_data = json.loads(output_file.read_text(encoding="utf-8"))
    assert len(saved_data) == 1
    assert saved_data[0]["id"] == "champ-ok"
    assert saved_data[0]["teams"] == [{"id": "team-2025", "name": "Team 2025"}]
    assert mock_get.call_count == 2


def test_sync_sfi_matches_from_json_updates_ended_match(
    tmp_path,
    sfi_competition_id,
    sfi_home_team_id,
    sfi_away_team_id,
):
    """sync_sfi_matches_from_json updates goals and date_time of an ENDED match."""
    competition = baker.make("core.Competition", sfi_id=sfi_competition_id)
    home_team = baker.make("core.Team", sfi_id=sfi_home_team_id, competitions=[competition])
    away_team = baker.make("core.Team", sfi_id=sfi_away_team_id, competitions=[competition])

    old_date_time = datetime(2026, 2, 25, 18, 0, 0, tzinfo=dt_timezone.utc)
    existing_match = baker.make(
        "core.Match",
        sfi_id="match-json-ended-001",
        competition=competition,
        home_team=home_team,
        away_team=away_team,
        status=Match.NOT_STARTED,
        home_goals=None,
        away_goals=None,
        date_time=old_date_time,
    )

    json_file = tmp_path / "matches.json"
    json_file.write_text(
        json.dumps({
            "result": [
                {
                    "id": "match-json-ended-001",
                    "date": "2026-02-26 20:00:00",
                    "status": "ENDED",
                    "timer": "90:00",
                    "championship": {"id": sfi_competition_id, "name": "Test League", "s_name": None},
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
            ]
        }),
        encoding="utf-8",
    )

    call_command("sync_sfi_matches_from_json", str(json_file))

    existing_match.refresh_from_db()
    assert existing_match.status == Match.FINSHED
    assert existing_match.home_goals == 2
    assert existing_match.away_goals == 1
    assert existing_match.date_time == datetime(2026, 2, 26, 20, 0, 0, tzinfo=dt_timezone.utc)


def test_sync_sfi_matches_from_json_updates_date_time_without_goal_change(
    tmp_path,
    sfi_competition_id,
    sfi_home_team_id,
    sfi_away_team_id,
):
    """date_time is updated even when goals and status are already correct."""
    competition = baker.make("core.Competition", sfi_id=sfi_competition_id)
    home_team = baker.make("core.Team", sfi_id=sfi_home_team_id, competitions=[competition])
    away_team = baker.make("core.Team", sfi_id=sfi_away_team_id, competitions=[competition])

    old_date_time = datetime(2026, 2, 25, 18, 0, 0, tzinfo=dt_timezone.utc)
    existing_match = baker.make(
        "core.Match",
        sfi_id="match-json-date-change",
        competition=competition,
        home_team=home_team,
        away_team=away_team,
        status=Match.FINSHED,
        home_goals=2,
        away_goals=1,
        date_time=old_date_time,
    )

    json_file = tmp_path / "matches.json"
    json_file.write_text(
        json.dumps({
            "result": [
                {
                    "id": "match-json-date-change",
                    "date": "2026-02-26 20:00:00",
                    "status": "ENDED",
                    "timer": "90:00",
                    "championship": {"id": sfi_competition_id, "name": "Test League", "s_name": None},
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
            ]
        }),
        encoding="utf-8",
    )

    call_command("sync_sfi_matches_from_json", str(json_file))

    existing_match.refresh_from_db()
    assert existing_match.date_time == datetime(2026, 2, 26, 20, 0, 0, tzinfo=dt_timezone.utc)
