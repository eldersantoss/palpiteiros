from datetime import date
from unittest.mock import patch

import pytest
from django.test import override_settings
from django.urls import reverse
from django.utils import timezone
from model_bakery import baker

pytestmark = pytest.mark.django_db


def _make_pool_with_guesser(competition=None):
    """Helper: creates a pool with its owner as guesser and an optional competition.

    Pool.created is backdated 2 days via queryset update so that get_matches()
    (which filters date_time__gt=pool.created) includes matches from the last 36h.
    """
    from core.models import GuessPool

    guesser = baker.make("core.Guesser")
    pool = baker.make("core.GuessPool", owner=guesser)
    GuessPool.objects.filter(pk=pool.pk).update(created=timezone.now() - timezone.timedelta(days=2))
    pool.refresh_from_db()
    if competition:
        pool.competitions.add(competition)
    return pool, guesser


def _open_match(pool, competition, home_team, away_team):
    """Creates a match that is open to guesses (starts in 1 hour)."""
    return baker.make(
        "core.Match",
        competition=competition,
        home_team=home_team,
        away_team=away_team,
        date_time=timezone.now() + timezone.timedelta(hours=1),
        status="NS",
        home_goals=None,
        away_goals=None,
    )


def _closed_match(pool, competition, home_team, away_team):
    """Creates a recent closed match (started 1 hour ago)."""
    return baker.make(
        "core.Match",
        competition=competition,
        home_team=home_team,
        away_team=away_team,
        date_time=timezone.now() - timezone.timedelta(hours=1),
        status="FT",
        home_goals=1,
        away_goals=0,
    )


def _about_to_start_match(competition, home_team, away_team, pool_minutes=5):
    """Creates a match inside the deadline window: starts before minutes_before_start_match."""
    return baker.make(
        "core.Match",
        competition=competition,
        home_team=home_team,
        away_team=away_team,
        date_time=timezone.now() + timezone.timedelta(minutes=pool_minutes - 1),
        status="NS",
        home_goals=None,
        away_goals=None,
    )


@override_settings(STATICFILES_STORAGE="django.contrib.staticfiles.storage.StaticFilesStorage")
def test_guesses_view_get_returns_200_with_open_matches(client):
    competition = baker.make("core.Competition")
    home_team = baker.make("core.Team", competitions=[competition])
    away_team = baker.make("core.Team", competitions=[competition])
    pool, guesser = _make_pool_with_guesser(competition)

    _open_match(pool, competition, home_team, away_team)

    client.force_login(guesser.user)
    response = client.get(reverse("core:guesses", kwargs={"pool_slug": pool.slug}))

    assert response.status_code == 200
    assert "guess_forms" in response.context
    assert len(response.context["guess_forms"]) == 1


@override_settings(STATICFILES_STORAGE="django.contrib.staticfiles.storage.StaticFilesStorage")
def test_guesses_view_get_closed_matches_appear_in_context(client):
    competition = baker.make("core.Competition")
    home_team = baker.make("core.Team", competitions=[competition])
    away_team = baker.make("core.Team", competitions=[competition])
    pool, guesser = _make_pool_with_guesser(competition)

    closed = _closed_match(pool, competition, home_team, away_team)
    open_ = _open_match(pool, competition, home_team, away_team)  # noqa: F841

    client.force_login(guesser.user)
    response = client.get(reverse("core:guesses", kwargs={"pool_slug": pool.slug}))

    assert response.status_code == 200
    closed_ids = [item["match"].id for item in response.context["closed_matches_and_guesses"]]
    assert closed.id in closed_ids


@override_settings(STATICFILES_STORAGE="django.contrib.staticfiles.storage.StaticFilesStorage")
def test_guesses_view_get_redirects_when_no_matches(client):
    competition = baker.make("core.Competition")
    pool, guesser = _make_pool_with_guesser(competition)

    client.force_login(guesser.user)
    response = client.get(reverse("core:guesses", kwargs={"pool_slug": pool.slug}))

    assert response.status_code == 302


@override_settings(STATICFILES_STORAGE="django.contrib.staticfiles.storage.StaticFilesStorage")
def test_guesses_view_get_owner_without_guesser_redirects(client):
    competition = baker.make("core.Competition")
    home_team = baker.make("core.Team", competitions=[competition])
    away_team = baker.make("core.Team", competitions=[competition])

    guesser = baker.make("core.Guesser")
    pool = baker.make("core.GuessPool", owner=guesser, competitions=[competition])
    # Remove owner from guessers so they are owner-only
    pool.guessers.remove(guesser)

    _open_match(pool, competition, home_team, away_team)

    client.force_login(guesser.user)
    response = client.get(reverse("core:guesses", kwargs={"pool_slug": pool.slug}))

    assert response.status_code == 302


@override_settings(STATICFILES_STORAGE="django.contrib.staticfiles.storage.StaticFilesStorage")
def test_guesses_view_post_saves_guess(client):
    competition = baker.make("core.Competition")
    home_team = baker.make("core.Team", competitions=[competition])
    away_team = baker.make("core.Team", competitions=[competition])
    pool, guesser = _make_pool_with_guesser(competition)

    match = _open_match(pool, competition, home_team, away_team)

    client.force_login(guesser.user)
    response = client.post(
        reverse("core:guesses", kwargs={"pool_slug": pool.slug}),
        {
            "csrfmiddlewaretoken": "dummy",
            f"home_goals_{match.id}": "2",
            f"away_goals_{match.id}": "1",
        },
    )

    assert response.status_code == 200
    assert pool.guesses.filter(guesser=guesser, match=match).exists()
    guess = pool.guesses.get(guesser=guesser, match=match)
    assert guess.home_goals == 2
    assert guess.away_goals == 1


@override_settings(STATICFILES_STORAGE="django.contrib.staticfiles.storage.StaticFilesStorage")
def test_guesses_view_post_for_all_pools_propagates_guess(client):
    competition = baker.make("core.Competition")
    home_team = baker.make("core.Team", competitions=[competition])
    away_team = baker.make("core.Team", competitions=[competition])

    guesser = baker.make("core.Guesser")
    pool1 = baker.make("core.GuessPool", owner=guesser, competitions=[competition])
    pool2 = baker.make("core.GuessPool", owner=guesser, competitions=[competition])

    match = _open_match(pool1, competition, home_team, away_team)

    client.force_login(guesser.user)
    response = client.post(
        reverse("core:guesses", kwargs={"pool_slug": pool1.slug}),
        {
            "csrfmiddlewaretoken": "dummy",
            f"home_goals_{match.id}": "3",
            f"away_goals_{match.id}": "0",
            "for_all_pools": "on",
        },
    )

    assert response.status_code == 200
    assert pool1.guesses.filter(guesser=guesser, match=match).exists()
    assert pool2.guesses.filter(guesser=guesser, match=match).exists()


@override_settings(STATICFILES_STORAGE="django.contrib.staticfiles.storage.StaticFilesStorage")
def test_guesses_view_post_redirects_when_no_open_matches(client):
    competition = baker.make("core.Competition")
    pool, guesser = _make_pool_with_guesser(competition)

    client.force_login(guesser.user)
    response = client.post(
        reverse("core:guesses", kwargs={"pool_slug": pool.slug}),
        {"csrfmiddlewaretoken": "dummy"},
    )

    assert response.status_code == 302


INSIDE_WINDOW = date(2026, 6, 15)
OUTSIDE_WINDOW = date(2026, 8, 1)


@override_settings(STATICFILES_STORAGE="django.contrib.staticfiles.storage.StaticFilesStorage")
@patch("core.views.timezone")
def test_guesses_world_cup_redirects_when_outside_date_window(mock_tz, client):
    mock_tz.localdate.return_value = OUTSIDE_WINDOW
    mock_tz.now = timezone.now
    mock_tz.timedelta = timezone.timedelta

    competition = baker.make("core.Competition")
    home_team = baker.make("core.Team", competitions=[competition])
    away_team = baker.make("core.Team", competitions=[competition])
    pool, guesser = _make_pool_with_guesser(competition)
    _open_match(pool, competition, home_team, away_team)

    client.force_login(guesser.user)
    response = client.get(reverse("core:guesses_world_cup", kwargs={"pool_slug": pool.slug}))

    # Outside the window, the view redirects to pool home (not guesses URL)
    assert response.status_code == 302


@override_settings(STATICFILES_STORAGE="django.contrib.staticfiles.storage.StaticFilesStorage")
@patch("core.views.timezone")
def test_guesses_world_cup_accessible_within_date_window(mock_tz, client):
    mock_tz.localdate.return_value = INSIDE_WINDOW
    mock_tz.now = timezone.now
    mock_tz.timedelta = timezone.timedelta

    competition = baker.make("core.Competition")
    home_team = baker.make("core.Team", competitions=[competition])
    away_team = baker.make("core.Team", competitions=[competition])
    pool, guesser = _make_pool_with_guesser(competition)
    _open_match(pool, competition, home_team, away_team)

    client.force_login(guesser.user)
    response = client.get(reverse("core:guesses_world_cup", kwargs={"pool_slug": pool.slug}))

    assert response.status_code == 200
    assert "groups_data" in response.context


@override_settings(STATICFILES_STORAGE="django.contrib.staticfiles.storage.StaticFilesStorage")
@patch("core.views.timezone")
def test_guesses_world_cup_matches_grouped_by_competition_group(mock_tz, client):
    mock_tz.localdate.return_value = INSIDE_WINDOW
    mock_tz.now = timezone.now
    mock_tz.timedelta = timezone.timedelta

    competition = baker.make("core.Competition")
    team_a1 = baker.make("core.Team", competitions=[competition])
    team_a2 = baker.make("core.Team", competitions=[competition])
    team_b1 = baker.make("core.Team", competitions=[competition])
    team_b2 = baker.make("core.Team", competitions=[competition])

    group_a = baker.make("core.CompetitionGroup", competition=competition, name="Grupo A")
    group_a.teams.set([team_a1, team_a2])
    group_b = baker.make("core.CompetitionGroup", competition=competition, name="Grupo B")
    group_b.teams.set([team_b1, team_b2])

    pool, guesser = _make_pool_with_guesser(competition)
    _open_match(pool, competition, team_a1, team_a2)
    _open_match(pool, competition, team_b1, team_b2)

    client.force_login(guesser.user)
    response = client.get(reverse("core:guesses_world_cup", kwargs={"pool_slug": pool.slug}))

    assert response.status_code == 200
    groups_data = response.context["groups_data"]
    group_names = [gd["group"].name for gd in groups_data if gd["group"]]
    assert "Grupo A" in group_names
    assert "Grupo B" in group_names
    assert len(groups_data) == 2


@override_settings(STATICFILES_STORAGE="django.contrib.staticfiles.storage.StaticFilesStorage")
@patch("core.views.timezone")
def test_guesses_world_cup_ungrouped_matches_appear_last(mock_tz, client):
    mock_tz.localdate.return_value = INSIDE_WINDOW
    mock_tz.now = timezone.now
    mock_tz.timedelta = timezone.timedelta

    competition = baker.make("core.Competition")
    team_a1 = baker.make("core.Team", competitions=[competition])
    team_a2 = baker.make("core.Team", competitions=[competition])
    ungrouped_home = baker.make("core.Team", competitions=[competition])
    ungrouped_away = baker.make("core.Team", competitions=[competition])

    group_a = baker.make("core.CompetitionGroup", competition=competition, name="Grupo A")
    group_a.teams.set([team_a1, team_a2])

    pool, guesser = _make_pool_with_guesser(competition)
    _open_match(pool, competition, team_a1, team_a2)
    _open_match(pool, competition, ungrouped_home, ungrouped_away)

    client.force_login(guesser.user)
    response = client.get(reverse("core:guesses_world_cup", kwargs={"pool_slug": pool.slug}))

    assert response.status_code == 200
    groups_data = response.context["groups_data"]
    assert len(groups_data) == 2
    # Last entry must be the ungrouped one
    assert groups_data[-1]["group"] is None


@override_settings(STATICFILES_STORAGE="django.contrib.staticfiles.storage.StaticFilesStorage")
@patch("core.views.timezone")
def test_guesses_world_cup_post_saves_guess(mock_tz, client):
    mock_tz.localdate.return_value = INSIDE_WINDOW
    mock_tz.now = timezone.now
    mock_tz.timedelta = timezone.timedelta

    competition = baker.make("core.Competition")
    home_team = baker.make("core.Team", competitions=[competition])
    away_team = baker.make("core.Team", competitions=[competition])
    pool, guesser = _make_pool_with_guesser(competition)
    match = _open_match(pool, competition, home_team, away_team)

    client.force_login(guesser.user)
    response = client.post(
        reverse("core:guesses_world_cup", kwargs={"pool_slug": pool.slug}),
        {
            "csrfmiddlewaretoken": "dummy",
            f"home_goals_{match.id}": "1",
            f"away_goals_{match.id}": "0",
        },
    )

    assert response.status_code == 200
    assert pool.guesses.filter(guesser=guesser, match=match).exists()
    guess = pool.guesses.get(guesser=guesser, match=match)
    assert guess.home_goals == 1
    assert guess.away_goals == 0


@override_settings(STATICFILES_STORAGE="django.contrib.staticfiles.storage.StaticFilesStorage")
@patch("core.views.timezone")
def test_guesses_world_cup_context_has_standings_key(mock_tz, client):
    mock_tz.localdate.return_value = INSIDE_WINDOW
    mock_tz.now = timezone.now
    mock_tz.timedelta = timezone.timedelta

    competition = baker.make("core.Competition")
    home_team = baker.make("core.Team", competitions=[competition])
    away_team = baker.make("core.Team", competitions=[competition])
    group = baker.make("core.CompetitionGroup", competition=competition, name="Grupo A")
    group.teams.set([home_team, away_team])
    pool, guesser = _make_pool_with_guesser(competition)
    _open_match(pool, competition, home_team, away_team)

    client.force_login(guesser.user)
    response = client.get(reverse("core:guesses_world_cup", kwargs={"pool_slug": pool.slug}))

    assert response.status_code == 200
    groups_data = response.context["groups_data"]
    assert "standings" in groups_data[0]


@override_settings(STATICFILES_STORAGE="django.contrib.staticfiles.storage.StaticFilesStorage")
@patch("core.views.timezone")
def test_guesses_world_cup_standings_reflects_closed_match_result(mock_tz, client):
    mock_tz.localdate.return_value = INSIDE_WINDOW
    mock_tz.now = timezone.now
    mock_tz.timedelta = timezone.timedelta

    competition = baker.make("core.Competition")
    home_team = baker.make("core.Team", competitions=[competition])
    away_team = baker.make("core.Team", competitions=[competition])
    group = baker.make("core.CompetitionGroup", competition=competition, name="Grupo A")
    group.teams.set([home_team, away_team])
    pool, guesser = _make_pool_with_guesser(competition)

    # A closed match that is already finished (status FT) contributes to standings
    baker.make(
        "core.Match",
        competition=competition,
        home_team=home_team,
        away_team=away_team,
        date_time=timezone.now() - timezone.timedelta(hours=1),
        status="FT",
        home_goals=2,
        away_goals=0,
    )
    _open_match(pool, competition, home_team, away_team)

    client.force_login(guesser.user)
    response = client.get(reverse("core:guesses_world_cup", kwargs={"pool_slug": pool.slug}))

    assert response.status_code == 200
    groups_data = response.context["groups_data"]
    group_entry = next(gd for gd in groups_data if gd["group"] and gd["group"].name == "Grupo A")
    standings = group_entry["standings"]
    home_entry = next(e for e in standings if e["team"] == home_team)
    assert home_entry["pts"] == 3
    assert home_entry["gf"] == 2


@override_settings(STATICFILES_STORAGE="django.contrib.staticfiles.storage.StaticFilesStorage")
@patch("core.views.timezone")
def test_guesses_world_cup_standings_empty_for_ungrouped_matches(mock_tz, client):
    mock_tz.localdate.return_value = INSIDE_WINDOW
    mock_tz.now = timezone.now
    mock_tz.timedelta = timezone.timedelta

    competition = baker.make("core.Competition")
    ungrouped_home = baker.make("core.Team", competitions=[competition])
    ungrouped_away = baker.make("core.Team", competitions=[competition])
    pool, guesser = _make_pool_with_guesser(competition)
    _open_match(pool, competition, ungrouped_home, ungrouped_away)

    client.force_login(guesser.user)
    response = client.get(reverse("core:guesses_world_cup", kwargs={"pool_slug": pool.slug}))

    assert response.status_code == 200
    groups_data = response.context["groups_data"]
    ungrouped_entry = next(gd for gd in groups_data if gd["group"] is None)
    assert ungrouped_entry["standings"] == []


@override_settings(STATICFILES_STORAGE="django.contrib.staticfiles.storage.StaticFilesStorage")
@patch("core.views.timezone")
def test_guesses_world_cup_owner_without_guesser_redirects(mock_tz, client):
    mock_tz.localdate.return_value = INSIDE_WINDOW
    mock_tz.now = timezone.now
    mock_tz.timedelta = timezone.timedelta

    competition = baker.make("core.Competition")
    home_team = baker.make("core.Team", competitions=[competition])
    away_team = baker.make("core.Team", competitions=[competition])

    guesser = baker.make("core.Guesser")
    pool = baker.make("core.GuessPool", owner=guesser, competitions=[competition])
    pool.guessers.remove(guesser)

    _open_match(pool, competition, home_team, away_team)

    client.force_login(guesser.user)
    response = client.get(reverse("core:guesses_world_cup", kwargs={"pool_slug": pool.slug}))

    assert response.status_code == 302


# --- minutes_before_start_match boundary tests ---


@override_settings(STATICFILES_STORAGE="django.contrib.staticfiles.storage.StaticFilesStorage")
def test_guesses_view_post_does_not_save_guess_past_deadline(client):
    """POST with data for a match inside the deadline window creates no Guess and redirects."""
    competition = baker.make("core.Competition")
    home_team = baker.make("core.Team", competitions=[competition])
    away_team = baker.make("core.Team", competitions=[competition])
    pool, guesser = _make_pool_with_guesser(competition)
    pool.minutes_before_start_match = 5
    pool.save()

    match = _about_to_start_match(competition, home_team, away_team, pool_minutes=5)

    client.force_login(guesser.user)
    response = client.post(
        reverse("core:guesses", kwargs={"pool_slug": pool.slug}),
        {
            "csrfmiddlewaretoken": "dummy",
            f"home_goals_{match.id}": "2",
            f"away_goals_{match.id}": "1",
        },
    )

    assert response.status_code == 302
    assert not pool.guesses.filter(guesser=guesser, match=match).exists()


@override_settings(STATICFILES_STORAGE="django.contrib.staticfiles.storage.StaticFilesStorage")
def test_guesses_view_post_saves_open_match_but_ignores_past_deadline(client):
    """When submitting both an open and a deadline-expired match, only the open one is saved."""
    competition = baker.make("core.Competition")
    home_team = baker.make("core.Team", competitions=[competition])
    away_team = baker.make("core.Team", competitions=[competition])
    pool, guesser = _make_pool_with_guesser(competition)
    pool.minutes_before_start_match = 5
    pool.save()

    open_match = _open_match(pool, competition, home_team, away_team)
    expired_match = _about_to_start_match(competition, home_team, away_team, pool_minutes=5)

    client.force_login(guesser.user)
    response = client.post(
        reverse("core:guesses", kwargs={"pool_slug": pool.slug}),
        {
            "csrfmiddlewaretoken": "dummy",
            f"home_goals_{open_match.id}": "1",
            f"away_goals_{open_match.id}": "0",
            f"home_goals_{expired_match.id}": "3",
            f"away_goals_{expired_match.id}": "2",
        },
    )

    assert response.status_code == 200
    assert pool.guesses.filter(guesser=guesser, match=open_match).exists()
    assert not pool.guesses.filter(guesser=guesser, match=expired_match).exists()


@override_settings(STATICFILES_STORAGE="django.contrib.staticfiles.storage.StaticFilesStorage")
@patch("core.views.timezone")
def test_guesses_world_cup_post_does_not_save_guess_past_deadline(mock_tz, client):
    """GroupedGuessesView POST ignores matches inside the deadline window."""
    mock_tz.localdate.return_value = INSIDE_WINDOW
    mock_tz.now = timezone.now
    mock_tz.timedelta = timezone.timedelta

    competition = baker.make("core.Competition")
    home_team = baker.make("core.Team", competitions=[competition])
    away_team = baker.make("core.Team", competitions=[competition])
    pool, guesser = _make_pool_with_guesser(competition)
    pool.minutes_before_start_match = 5
    pool.save()

    match = _about_to_start_match(competition, home_team, away_team, pool_minutes=5)

    client.force_login(guesser.user)
    response = client.post(
        reverse("core:guesses_world_cup", kwargs={"pool_slug": pool.slug}),
        {
            "csrfmiddlewaretoken": "dummy",
            f"home_goals_{match.id}": "2",
            f"away_goals_{match.id}": "1",
        },
    )

    assert response.status_code == 302
    assert not pool.guesses.filter(guesser=guesser, match=match).exists()


@override_settings(STATICFILES_STORAGE="django.contrib.staticfiles.storage.StaticFilesStorage")
@patch("core.views.timezone")
def test_guesses_world_cup_post_saves_open_match_but_ignores_past_deadline(mock_tz, client):
    """GroupedGuessesView POST saves open matches and ignores deadline-expired ones."""
    mock_tz.localdate.return_value = INSIDE_WINDOW
    mock_tz.now = timezone.now
    mock_tz.timedelta = timezone.timedelta

    competition = baker.make("core.Competition")
    home_team = baker.make("core.Team", competitions=[competition])
    away_team = baker.make("core.Team", competitions=[competition])
    pool, guesser = _make_pool_with_guesser(competition)
    pool.minutes_before_start_match = 5
    pool.save()

    open_match = _open_match(pool, competition, home_team, away_team)
    expired_match = _about_to_start_match(competition, home_team, away_team, pool_minutes=5)

    client.force_login(guesser.user)
    response = client.post(
        reverse("core:guesses_world_cup", kwargs={"pool_slug": pool.slug}),
        {
            "csrfmiddlewaretoken": "dummy",
            f"home_goals_{open_match.id}": "1",
            f"away_goals_{open_match.id}": "0",
            f"home_goals_{expired_match.id}": "3",
            f"away_goals_{expired_match.id}": "2",
        },
    )

    assert response.status_code == 200
    assert pool.guesses.filter(guesser=guesser, match=open_match).exists()
    assert not pool.guesses.filter(guesser=guesser, match=expired_match).exists()


# ---------------------------------------------------------------------------
# GuessForm partial-submission unit tests
# ---------------------------------------------------------------------------


def _make_match():
    competition = baker.make("core.Competition")
    home_team = baker.make("core.Team", competitions=[competition])
    away_team = baker.make("core.Team", competitions=[competition])
    return baker.make(
        "core.Match",
        competition=competition,
        home_team=home_team,
        away_team=away_team,
        date_time=timezone.now() + timezone.timedelta(hours=1),
        status="NS",
        home_goals=None,
        away_goals=None,
    )


def test_guess_form_valid_when_both_fields_filled():
    from core.forms import GuessForm

    match = _make_match()
    form = GuessForm(
        {f"home_goals_{match.id}": "2", f"away_goals_{match.id}": "1"},
        match=match,
    )
    assert form.is_valid()
    assert form.has_valid_guess_data()


def test_guess_form_valid_when_both_fields_empty():
    from core.forms import GuessForm

    match = _make_match()
    form = GuessForm({}, match=match)
    assert form.is_valid()
    assert not form.has_valid_guess_data()


def test_guess_form_invalid_when_only_home_filled():
    from core.forms import GuessForm

    match = _make_match()
    form = GuessForm({f"home_goals_{match.id}": "2"}, match=match)
    assert not form.is_valid()


def test_guess_form_invalid_when_only_away_filled():
    from core.forms import GuessForm

    match = _make_match()
    form = GuessForm({f"away_goals_{match.id}": "1"}, match=match)
    assert not form.is_valid()


# ---------------------------------------------------------------------------
# GuessesView partial-submission integration tests
# ---------------------------------------------------------------------------


@override_settings(STATICFILES_STORAGE="django.contrib.staticfiles.storage.StaticFilesStorage")
def test_guesses_view_post_partial_saves_only_filled_guess(client):
    """POST with data for only one of two open matches saves only that match."""
    competition = baker.make("core.Competition")
    home_team = baker.make("core.Team", competitions=[competition])
    away_team = baker.make("core.Team", competitions=[competition])
    pool, guesser = _make_pool_with_guesser(competition)

    match1 = _open_match(pool, competition, home_team, away_team)
    match2 = _open_match(pool, competition, home_team, away_team)

    client.force_login(guesser.user)
    response = client.post(
        reverse("core:guesses", kwargs={"pool_slug": pool.slug}),
        {
            "csrfmiddlewaretoken": "dummy",
            f"home_goals_{match1.id}": "2",
            f"away_goals_{match1.id}": "1",
        },
    )

    assert response.status_code == 200
    assert pool.guesses.filter(guesser=guesser, match=match1).exists()
    assert not pool.guesses.filter(guesser=guesser, match=match2).exists()


@override_settings(STATICFILES_STORAGE="django.contrib.staticfiles.storage.StaticFilesStorage")
def test_guesses_view_post_empty_submission_saves_nothing(client):
    """POST with all fields empty creates no guesses and returns 200."""
    competition = baker.make("core.Competition")
    home_team = baker.make("core.Team", competitions=[competition])
    away_team = baker.make("core.Team", competitions=[competition])
    pool, guesser = _make_pool_with_guesser(competition)

    _open_match(pool, competition, home_team, away_team)

    client.force_login(guesser.user)
    response = client.post(
        reverse("core:guesses", kwargs={"pool_slug": pool.slug}),
        {"csrfmiddlewaretoken": "dummy"},
    )

    assert response.status_code == 200
    assert not pool.guesses.filter(guesser=guesser).exists()


# ---------------------------------------------------------------------------
# GroupedGuessesView partial-submission integration tests
# ---------------------------------------------------------------------------


@override_settings(STATICFILES_STORAGE="django.contrib.staticfiles.storage.StaticFilesStorage")
@patch("core.views.timezone")
def test_guesses_world_cup_post_partial_saves_only_filled_guess(mock_tz, client):
    """GroupedGuessesView POST with data for only one of two open matches saves only that match."""
    mock_tz.localdate.return_value = INSIDE_WINDOW
    mock_tz.now = timezone.now
    mock_tz.timedelta = timezone.timedelta

    competition = baker.make("core.Competition")
    home_team = baker.make("core.Team", competitions=[competition])
    away_team = baker.make("core.Team", competitions=[competition])
    pool, guesser = _make_pool_with_guesser(competition)

    match1 = _open_match(pool, competition, home_team, away_team)
    match2 = _open_match(pool, competition, home_team, away_team)

    client.force_login(guesser.user)
    response = client.post(
        reverse("core:guesses_world_cup", kwargs={"pool_slug": pool.slug}),
        {
            "csrfmiddlewaretoken": "dummy",
            f"home_goals_{match1.id}": "3",
            f"away_goals_{match1.id}": "0",
        },
    )

    assert response.status_code == 200
    assert pool.guesses.filter(guesser=guesser, match=match1).exists()
    assert not pool.guesses.filter(guesser=guesser, match=match2).exists()


@override_settings(STATICFILES_STORAGE="django.contrib.staticfiles.storage.StaticFilesStorage")
@patch("core.views.timezone")
def test_guesses_world_cup_post_empty_submission_saves_nothing(mock_tz, client):
    """GroupedGuessesView POST with all fields empty creates no guesses and returns 200."""
    mock_tz.localdate.return_value = INSIDE_WINDOW
    mock_tz.now = timezone.now
    mock_tz.timedelta = timezone.timedelta

    competition = baker.make("core.Competition")
    home_team = baker.make("core.Team", competitions=[competition])
    away_team = baker.make("core.Team", competitions=[competition])
    pool, guesser = _make_pool_with_guesser(competition)

    _open_match(pool, competition, home_team, away_team)

    client.force_login(guesser.user)
    response = client.post(
        reverse("core:guesses_world_cup", kwargs={"pool_slug": pool.slug}),
        {"csrfmiddlewaretoken": "dummy"},
    )

    assert response.status_code == 200
    assert not pool.guesses.filter(guesser=guesser).exists()
