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
def test_grouped_guesses_redirects_when_outside_date_window(mock_tz, client):
    mock_tz.localdate.return_value = OUTSIDE_WINDOW
    mock_tz.now = timezone.now
    mock_tz.timedelta = timezone.timedelta

    competition = baker.make("core.Competition")
    home_team = baker.make("core.Team", competitions=[competition])
    away_team = baker.make("core.Team", competitions=[competition])
    pool, guesser = _make_pool_with_guesser(competition)
    _open_match(pool, competition, home_team, away_team)

    client.force_login(guesser.user)
    response = client.get(reverse("core:grouped_guesses", kwargs={"pool_slug": pool.slug}))

    # Outside the window, the view redirects to pool home (not guesses URL)
    assert response.status_code == 302


@override_settings(STATICFILES_STORAGE="django.contrib.staticfiles.storage.StaticFilesStorage")
@patch("core.views.timezone")
def test_grouped_guesses_accessible_within_date_window(mock_tz, client):
    mock_tz.localdate.return_value = INSIDE_WINDOW
    mock_tz.now = timezone.now
    mock_tz.timedelta = timezone.timedelta

    competition = baker.make("core.Competition")
    home_team = baker.make("core.Team", competitions=[competition])
    away_team = baker.make("core.Team", competitions=[competition])
    pool, guesser = _make_pool_with_guesser(competition)
    _open_match(pool, competition, home_team, away_team)

    client.force_login(guesser.user)
    response = client.get(reverse("core:grouped_guesses", kwargs={"pool_slug": pool.slug}))

    assert response.status_code == 200
    assert "groups_data" in response.context


@override_settings(STATICFILES_STORAGE="django.contrib.staticfiles.storage.StaticFilesStorage")
@patch("core.views.timezone")
def test_grouped_guesses_matches_grouped_by_competition_group(mock_tz, client):
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
    response = client.get(reverse("core:grouped_guesses", kwargs={"pool_slug": pool.slug}))

    assert response.status_code == 200
    groups_data = response.context["groups_data"]
    group_names = [gd["group"].name for gd in groups_data if gd["group"]]
    assert "Grupo A" in group_names
    assert "Grupo B" in group_names
    assert len(groups_data) == 2


@override_settings(STATICFILES_STORAGE="django.contrib.staticfiles.storage.StaticFilesStorage")
@patch("core.views.timezone")
def test_grouped_guesses_ungrouped_matches_appear_last(mock_tz, client):
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
    response = client.get(reverse("core:grouped_guesses", kwargs={"pool_slug": pool.slug}))

    assert response.status_code == 200
    groups_data = response.context["groups_data"]
    assert len(groups_data) == 2
    # Last entry must be the ungrouped one
    assert groups_data[-1]["group"] is None


@override_settings(STATICFILES_STORAGE="django.contrib.staticfiles.storage.StaticFilesStorage")
@patch("core.views.timezone")
def test_grouped_guesses_post_saves_guess(mock_tz, client):
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
        reverse("core:grouped_guesses", kwargs={"pool_slug": pool.slug}),
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
def test_grouped_guesses_owner_without_guesser_redirects(mock_tz, client):
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
    response = client.get(reverse("core:grouped_guesses", kwargs={"pool_slug": pool.slug}))

    assert response.status_code == 302
