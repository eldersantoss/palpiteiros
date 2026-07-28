import pytest
from django.utils import timezone
from model_bakery import baker
from unittest.mock import patch

pytestmark = pytest.mark.django_db


def test_get_matches():
    competition = baker.make("core.Competition")
    competition_teams = baker.make("core.Team", 2)
    competition.teams.set(competition_teams)

    without_competition_teams = baker.make("core.Team", 1)

    guess_pool = baker.make("core.GuessPool")
    guess_pool.competitions.add(competition)
    guess_pool.teams.set(without_competition_teams)

    assert guess_pool.competitions.count() == 1
    assert guess_pool.teams.count() == len(without_competition_teams)

    # Guess Pool should have matches of competitions and teams created after himself
    baker.make("core.Match", competition=competition, home_team=competition_teams[0], away_team=competition_teams[1])
    baker.make("core.Match", home_team=competition_teams[0], away_team=without_competition_teams[0])
    assert guess_pool.get_matches().count() == 2

    # Once added to Guess Pool, a match should remain in it even if teams involved have been removed from a registered competition
    competition.teams.clear()
    assert guess_pool.get_matches().count() == 2


def _make_pool_with_old_created(**kwargs):
    """Create a GuessPool with created set far in the past so get_matches() doesn't filter out past matches."""
    pool = baker.make("core.GuessPool", **kwargs)
    GuessPool = pool.__class__
    GuessPool.objects.filter(pk=pool.pk).update(created=timezone.make_aware(timezone.datetime(2020, 1, 1)))
    pool.refresh_from_db()
    return pool


@patch("core.models.timezone")
def test_get_closed_recent_matches_returns_matches_within_window(mock_tz):
    mock_tz.now.return_value = timezone.make_aware(timezone.datetime(2026, 6, 6, 12, 0, 0))
    mock_tz.timedelta = timezone.timedelta

    pool = _make_pool_with_old_created(hours_to_keep_closed_matches_in_ranking=36, minutes_before_start_match=5)
    competition = baker.make("core.Competition")
    pool.competitions.add(competition)
    teams = baker.make("core.Team", 2)
    competition.teams.set(teams)

    # Match 10 hours ago — within 36h window, already closed
    recent_match = baker.make(
        "core.Match",
        competition=competition,
        home_team=teams[0],
        away_team=teams[1],
        date_time=mock_tz.now.return_value - timezone.timedelta(hours=10),
    )
    # Match 40 hours ago — outside 36h window
    baker.make(
        "core.Match",
        competition=competition,
        home_team=teams[0],
        away_team=teams[1],
        date_time=mock_tz.now.return_value - timezone.timedelta(hours=40),
    )

    result = pool.get_closed_recent_matches()
    assert result.count() == 1
    assert result.first() == recent_match


@patch("core.models.timezone")
def test_get_closed_recent_matches_excludes_open_matches(mock_tz):
    mock_tz.now.return_value = timezone.make_aware(timezone.datetime(2026, 6, 6, 12, 0, 0))
    mock_tz.timedelta = timezone.timedelta

    pool = _make_pool_with_old_created(hours_to_keep_closed_matches_in_ranking=36, minutes_before_start_match=5)
    competition = baker.make("core.Competition")
    pool.competitions.add(competition)
    teams = baker.make("core.Team", 2)
    competition.teams.set(teams)

    # Match in 10 minutes — still open (within minutes_before_start_match threshold)
    baker.make(
        "core.Match",
        competition=competition,
        home_team=teams[0],
        away_team=teams[1],
        date_time=mock_tz.now.return_value + timezone.timedelta(minutes=10),
    )

    result = pool.get_closed_recent_matches()
    assert result.count() == 0


@patch("core.models.timezone")
def test_get_closed_recent_matches_respects_custom_hours_window(mock_tz):
    mock_tz.now.return_value = timezone.make_aware(timezone.datetime(2026, 6, 6, 12, 0, 0))
    mock_tz.timedelta = timezone.timedelta

    pool = _make_pool_with_old_created(hours_to_keep_closed_matches_in_ranking=12, minutes_before_start_match=5)
    competition = baker.make("core.Competition")
    pool.competitions.add(competition)
    teams = baker.make("core.Team", 2)
    competition.teams.set(teams)

    # Match 6 hours ago — within 12h window
    match_in_window = baker.make(
        "core.Match",
        competition=competition,
        home_team=teams[0],
        away_team=teams[1],
        date_time=mock_tz.now.return_value - timezone.timedelta(hours=6),
    )
    # Match 20 hours ago — outside 12h window
    baker.make(
        "core.Match",
        competition=competition,
        home_team=teams[0],
        away_team=teams[1],
        date_time=mock_tz.now.return_value - timezone.timedelta(hours=20),
    )

    result = pool.get_closed_recent_matches()
    assert result.count() == 1
    assert result.first() == match_in_window


@patch("core.models.timezone")
def test_get_closed_recent_matches_ordered_by_most_recent_first(mock_tz):
    mock_tz.now.return_value = timezone.make_aware(timezone.datetime(2026, 6, 6, 12, 0, 0))
    mock_tz.timedelta = timezone.timedelta

    pool = _make_pool_with_old_created(hours_to_keep_closed_matches_in_ranking=36, minutes_before_start_match=5)
    competition = baker.make("core.Competition")
    pool.competitions.add(competition)
    teams = baker.make("core.Team", 4)
    competition.teams.set(teams)

    match_5h_ago = baker.make(
        "core.Match",
        competition=competition,
        home_team=teams[0],
        away_team=teams[1],
        date_time=mock_tz.now.return_value - timezone.timedelta(hours=5),
    )
    match_20h_ago = baker.make(
        "core.Match",
        competition=competition,
        home_team=teams[2],
        away_team=teams[3],
        date_time=mock_tz.now.return_value - timezone.timedelta(hours=20),
    )

    result = list(pool.get_closed_recent_matches())
    assert result[0] == match_5h_ago
    assert result[1] == match_20h_ago


@patch("core.models.timezone")
def test_get_relevant_matches_equals_separate_calls(mock_tz):
    """get_relevant_matches() must return the same match sets as
    get_open_matches() + get_closed_recent_matches() called separately."""
    mock_tz.now.return_value = timezone.make_aware(timezone.datetime(2026, 6, 6, 12, 0, 0))
    mock_tz.timedelta = timezone.timedelta

    pool = _make_pool_with_old_created(
        hours_to_keep_closed_matches_in_ranking=36,
        minutes_before_start_match=5,
        hours_before_open_to_guesses=48,
    )
    competition = baker.make("core.Competition")
    pool.competitions.add(competition)
    teams = baker.make("core.Team", 6)
    competition.teams.set(teams)

    now = mock_tz.now.return_value

    # Open match (starts in 1 hour — within the open window)
    open_match = baker.make(
        "core.Match",
        competition=competition,
        home_team=teams[0],
        away_team=teams[1],
        date_time=now + timezone.timedelta(hours=1),
    )
    # Closed recent match (started 2 hours ago — within the closed window)
    closed_recent = baker.make(
        "core.Match",
        competition=competition,
        home_team=teams[2],
        away_team=teams[3],
        date_time=now - timezone.timedelta(hours=2),
    )
    # Match outside window (started 40 hours ago — outside closed window)
    baker.make(
        "core.Match",
        competition=competition,
        home_team=teams[4],
        away_team=teams[5],
        date_time=now - timezone.timedelta(hours=40),
    )

    # Results from separate calls
    expected_open_ids = set(pool.get_open_matches().values_list("id", flat=True))
    expected_closed_ids = set(pool.get_closed_recent_matches().values_list("id", flat=True))

    # Results from unified call
    open_matches, closed_matches = pool.get_relevant_matches()
    actual_open_ids = {m.id for m in open_matches}
    actual_closed_ids = {m.id for m in closed_matches}

    assert actual_open_ids == expected_open_ids
    assert actual_closed_ids == expected_closed_ids
    assert open_match.id in actual_open_ids
    assert closed_recent.id in actual_closed_ids
