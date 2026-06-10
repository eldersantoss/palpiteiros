"""
Tests for the `for_all_pools` feature.

When a user checks "Aproveitar palpites em todos os bolões" in GuessesView,
the submitted guesses should be propagated to every other pool that:
  - the same guesser belongs to (via the `guessers` M2M), AND
  - contains the same match (via competitions or teams M2M).

When unchecked, guesses stay only in the pool being used.

GuessesView  → template guesses.html          → has the checkbox
GroupedGuessesView → template guesses_by_group.html → does NOT have the checkbox

The absence of the checkbox means the POST body will never contain
`for_all_pools`, so `bool(request.POST.get("for_all_pools"))` is False,
meaning GroupedGuessesView must NEVER propagate guesses to other pools —
even if the match exists in multiple pools.

Test plan
---------
GuessesView (for_all_pools=True):
  1. Guess is saved in the originating pool.
  2. Guess is propagated to a second pool sharing the same match + guesser.
  3. Guess is NOT propagated to a pool that shares the match but not the guesser.
  4. Guess is NOT propagated to a pool that shares the guesser but not the match.
  5. Propagation replaces an existing guess (same match) in the other pool.

GuessesView (for_all_pools=False / unchecked):
  6. Guess is saved only in the originating pool, not in any other pool.

GroupedGuessesView (no checkbox in template → for_all_pools always False):
  7. Guess is saved in the originating pool.
  8. Guess is NOT propagated to any other pool regardless of membership/match.
  9. The view never reads `for_all_pools=True`, even if injected via POST.
"""

from datetime import date
from unittest.mock import patch

import pytest
from django.test import override_settings
from django.urls import reverse
from django.utils import timezone
from model_bakery import baker

pytestmark = pytest.mark.django_db

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

INSIDE_WC_WINDOW = date(2026, 6, 15)


def _make_pool_with_guesser(competition=None):
    """Creates a pool whose owner is automatically also a guesser."""
    from core.models import GuessPool

    guesser = baker.make("core.Guesser")
    pool = baker.make("core.GuessPool", owner=guesser)
    GuessPool.objects.filter(pk=pool.pk).update(created=timezone.now() - timezone.timedelta(days=2))
    pool.refresh_from_db()
    if competition:
        pool.competitions.add(competition)
    return pool, guesser


def _second_pool_for_guesser(guesser, competition=None):
    """Creates a second pool and adds an existing guesser as a member (not owner)."""
    from core.models import GuessPool

    owner2 = baker.make("core.Guesser")
    pool = baker.make("core.GuessPool", owner=owner2)
    GuessPool.objects.filter(pk=pool.pk).update(created=timezone.now() - timezone.timedelta(days=2))
    pool.refresh_from_db()
    if competition:
        pool.competitions.add(competition)
    # Add the first guesser as a regular member
    pool.guessers.add(guesser)
    return pool


def _open_match(competition, home_team, away_team):
    """Match that is open to guesses (starts in 2 hours, status NS)."""
    return baker.make(
        "core.Match",
        competition=competition,
        home_team=home_team,
        away_team=away_team,
        date_time=timezone.now() + timezone.timedelta(hours=2),
        status="NS",
        home_goals=None,
        away_goals=None,
    )


def _post_guess(client, url, match, home_goals, away_goals, for_all_pools=False):
    data = {
        "csrfmiddlewaretoken": "dummy",
        f"home_goals_{match.id}": str(home_goals),
        f"away_goals_{match.id}": str(away_goals),
    }
    if for_all_pools:
        data["for_all_pools"] = "on"
    return client.post(url, data)


# ---------------------------------------------------------------------------
# GuessesView – for_all_pools = True
# ---------------------------------------------------------------------------


@override_settings(STATICFILES_STORAGE="django.contrib.staticfiles.storage.StaticFilesStorage")
def test_guesses_view_for_all_pools_saves_in_originating_pool(client):
    """Guess is saved in the pool from which the form was submitted."""
    competition = baker.make("core.Competition")
    home = baker.make("core.Team", competitions=[competition])
    away = baker.make("core.Team", competitions=[competition])
    pool, guesser = _make_pool_with_guesser(competition)
    match = _open_match(competition, home, away)

    client.force_login(guesser.user)
    response = _post_guess(
        client,
        reverse("core:guesses", kwargs={"pool_slug": pool.slug}),
        match,
        2,
        1,
        for_all_pools=True,
    )

    assert response.status_code == 200
    assert pool.guesses.filter(guesser=guesser, match=match).exists()


@override_settings(STATICFILES_STORAGE="django.contrib.staticfiles.storage.StaticFilesStorage")
def test_guesses_view_for_all_pools_propagates_to_other_pool_with_same_match(client):
    """When for_all_pools=True, guess also appears in a second pool that shares the match and guesser."""
    competition = baker.make("core.Competition")
    home = baker.make("core.Team", competitions=[competition])
    away = baker.make("core.Team", competitions=[competition])
    pool1, guesser = _make_pool_with_guesser(competition)
    pool2 = _second_pool_for_guesser(guesser, competition)
    match = _open_match(competition, home, away)

    client.force_login(guesser.user)
    _post_guess(
        client,
        reverse("core:guesses", kwargs={"pool_slug": pool1.slug}),
        match,
        3,
        0,
        for_all_pools=True,
    )

    assert pool1.guesses.filter(guesser=guesser, match=match).exists()
    assert pool2.guesses.filter(guesser=guesser, match=match).exists()
    # Both pools must hold the exact same Guess instance
    guess1 = pool1.guesses.get(guesser=guesser, match=match)
    guess2 = pool2.guesses.get(guesser=guesser, match=match)
    assert guess1.pk == guess2.pk


@override_settings(STATICFILES_STORAGE="django.contrib.staticfiles.storage.StaticFilesStorage")
def test_guesses_view_for_all_pools_does_not_propagate_when_guesser_not_member(client):
    """Guess must NOT reach a pool where the submitter is not a member, even if the match is there."""
    competition = baker.make("core.Competition")
    home = baker.make("core.Team", competitions=[competition])
    away = baker.make("core.Team", competitions=[competition])
    pool1, guesser = _make_pool_with_guesser(competition)

    # pool3 has the same competition (so the match belongs to it) but guesser is NOT a member
    owner3 = baker.make("core.Guesser")
    pool3 = baker.make("core.GuessPool", owner=owner3)
    from core.models import GuessPool
    GuessPool.objects.filter(pk=pool3.pk).update(created=timezone.now() - timezone.timedelta(days=2))
    pool3.refresh_from_db()
    pool3.competitions.add(competition)

    match = _open_match(competition, home, away)

    client.force_login(guesser.user)
    _post_guess(
        client,
        reverse("core:guesses", kwargs={"pool_slug": pool1.slug}),
        match,
        1,
        1,
        for_all_pools=True,
    )

    assert pool1.guesses.filter(guesser=guesser, match=match).exists()
    assert not pool3.guesses.filter(guesser=guesser, match=match).exists()


@override_settings(STATICFILES_STORAGE="django.contrib.staticfiles.storage.StaticFilesStorage")
def test_guesses_view_for_all_pools_does_not_propagate_when_pool_lacks_match(client):
    """Guess must NOT reach a pool where the guesser is a member but the match does not belong."""
    competition_a = baker.make("core.Competition")
    competition_b = baker.make("core.Competition")
    home = baker.make("core.Team", competitions=[competition_a])
    away = baker.make("core.Team", competitions=[competition_a])
    pool1, guesser = _make_pool_with_guesser(competition_a)
    # pool2: guesser is a member but tracks competition_b, not competition_a
    pool2 = _second_pool_for_guesser(guesser, competition_b)

    match = _open_match(competition_a, home, away)

    client.force_login(guesser.user)
    _post_guess(
        client,
        reverse("core:guesses", kwargs={"pool_slug": pool1.slug}),
        match,
        2,
        2,
        for_all_pools=True,
    )

    assert pool1.guesses.filter(guesser=guesser, match=match).exists()
    assert not pool2.guesses.filter(guesser=guesser, match=match).exists()


@override_settings(STATICFILES_STORAGE="django.contrib.staticfiles.storage.StaticFilesStorage")
def test_guesses_view_for_all_pools_replaces_existing_guess_in_other_pool(client):
    """When for_all_pools=True and another pool already has a guess for the same match,
    the old guess is removed and replaced by the new one."""
    competition = baker.make("core.Competition")
    home = baker.make("core.Team", competitions=[competition])
    away = baker.make("core.Team", competitions=[competition])
    pool1, guesser = _make_pool_with_guesser(competition)
    pool2 = _second_pool_for_guesser(guesser, competition)
    match = _open_match(competition, home, away)

    # Create a pre-existing guess in pool2
    from core.models import Guess
    old_guess = Guess.objects.create(guesser=guesser, match=match, home_goals=0, away_goals=0)
    pool2.guesses.add(old_guess)
    old_guess_pk = old_guess.pk

    client.force_login(guesser.user)
    _post_guess(
        client,
        reverse("core:guesses", kwargs={"pool_slug": pool1.slug}),
        match,
        4,
        1,
        for_all_pools=True,
    )

    # Old guess removed from pool2
    assert not pool2.guesses.filter(pk=old_guess_pk).exists()
    # New guess present in pool2 with updated scores
    new_guess = pool2.guesses.get(guesser=guesser, match=match)
    assert new_guess.home_goals == 4
    assert new_guess.away_goals == 1


# ---------------------------------------------------------------------------
# GuessesView – for_all_pools = False (checkbox unchecked)
# ---------------------------------------------------------------------------


@override_settings(STATICFILES_STORAGE="django.contrib.staticfiles.storage.StaticFilesStorage")
def test_guesses_view_without_for_all_pools_does_not_propagate(client):
    """When for_all_pools is NOT checked, guess stays only in the originating pool."""
    competition = baker.make("core.Competition")
    home = baker.make("core.Team", competitions=[competition])
    away = baker.make("core.Team", competitions=[competition])
    pool1, guesser = _make_pool_with_guesser(competition)
    pool2 = _second_pool_for_guesser(guesser, competition)
    match = _open_match(competition, home, away)

    client.force_login(guesser.user)
    # for_all_pools NOT sent → False
    _post_guess(
        client,
        reverse("core:guesses", kwargs={"pool_slug": pool1.slug}),
        match,
        1,
        0,
        for_all_pools=False,
    )

    assert pool1.guesses.filter(guesser=guesser, match=match).exists()
    assert not pool2.guesses.filter(guesser=guesser, match=match).exists()


# ---------------------------------------------------------------------------
# GroupedGuessesView – checkbox absent → for_all_pools is always False
# ---------------------------------------------------------------------------


@override_settings(STATICFILES_STORAGE="django.contrib.staticfiles.storage.StaticFilesStorage")
@patch("core.views.timezone")
def test_grouped_guesses_view_saves_in_originating_pool(mock_tz, client):
    """GroupedGuessesView saves the guess in the pool from which the form was submitted."""
    mock_tz.localdate.return_value = INSIDE_WC_WINDOW
    mock_tz.now = timezone.now
    mock_tz.timedelta = timezone.timedelta

    competition = baker.make("core.Competition")
    home = baker.make("core.Team", competitions=[competition])
    away = baker.make("core.Team", competitions=[competition])
    pool, guesser = _make_pool_with_guesser(competition)
    match = _open_match(competition, home, away)

    client.force_login(guesser.user)
    response = _post_guess(
        client,
        reverse("core:guesses_world_cup", kwargs={"pool_slug": pool.slug}),
        match,
        2,
        0,
    )

    assert response.status_code == 200
    assert pool.guesses.filter(guesser=guesser, match=match).exists()


@override_settings(STATICFILES_STORAGE="django.contrib.staticfiles.storage.StaticFilesStorage")
@patch("core.views.timezone")
def test_grouped_guesses_view_always_propagates(mock_tz, client):
    """GroupedGuessesView must always propagate guesses to other pools because
    for_all_pools is hardcoded to True for grouped guesses."""
    mock_tz.localdate.return_value = INSIDE_WC_WINDOW
    mock_tz.now = timezone.now
    mock_tz.timedelta = timezone.timedelta

    competition = baker.make("core.Competition")
    home = baker.make("core.Team", competitions=[competition])
    away = baker.make("core.Team", competitions=[competition])
    pool1, guesser = _make_pool_with_guesser(competition)
    pool2 = _second_pool_for_guesser(guesser, competition)
    match = _open_match(competition, home, away)

    client.force_login(guesser.user)
    # No for_all_pools in the POST (matches what the template actually sends)
    _post_guess(
        client,
        reverse("core:guesses_world_cup", kwargs={"pool_slug": pool1.slug}),
        match,
        1,
        1,
        for_all_pools=False,
    )

    assert pool1.guesses.filter(guesser=guesser, match=match).exists()
    assert pool2.guesses.filter(guesser=guesser, match=match).exists()


@override_settings(STATICFILES_STORAGE="django.contrib.staticfiles.storage.StaticFilesStorage")
@patch("core.views.timezone")
def test_grouped_guesses_view_propagates_regardless_of_injected_for_all_pools(mock_tz, client):
    """GroupedGuessesView propagates guesses to other pools regardless of the injected
    value of for_all_pools, since it is hardcoded to True.
    """
    mock_tz.localdate.return_value = INSIDE_WC_WINDOW
    mock_tz.now = timezone.now
    mock_tz.timedelta = timezone.timedelta

    competition = baker.make("core.Competition")
    home = baker.make("core.Team", competitions=[competition])
    away = baker.make("core.Team", competitions=[competition])
    pool1, guesser = _make_pool_with_guesser(competition)
    pool2 = _second_pool_for_guesser(guesser, competition)
    match = _open_match(competition, home, away)

    client.force_login(guesser.user)
    _post_guess(
        client,
        reverse("core:guesses_world_cup", kwargs={"pool_slug": pool1.slug}),
        match,
        2,
        2,
        for_all_pools=True,
    )

    assert pool1.guesses.filter(guesser=guesser, match=match).exists()
    assert pool2.guesses.filter(guesser=guesser, match=match).exists()
