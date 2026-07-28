from datetime import date, datetime
from unittest.mock import patch

import pytest
from django.test import override_settings
from django.urls import reverse
from django.utils import timezone
from model_bakery import baker

from core.constants import WORLD_CUP_PERIOD_DATE_RANGES
from core.forms import WorldCupRankingPeriodForm
from core.models import WorldCupRankingEntry

pytestmark = pytest.mark.django_db

URL_NAME = "core:world_cup_ranking"
INSIDE_PERIOD = date(2026, 6, 15)
OUTSIDE_PERIOD = date(2026, 5, 1)


# ---------------------------------------------------------------------------
# Form tests
# ---------------------------------------------------------------------------


def test_form_default_returns_geral_dates():
    form = WorldCupRankingPeriodForm({})
    form.is_valid()
    assert form.get_period_dates() == WORLD_CUP_PERIOD_DATE_RANGES["geral"]


def test_form_empty_periodo_returns_geral_dates():
    form = WorldCupRankingPeriodForm({"periodo": ""})
    form.is_valid()
    assert form.get_period_dates() == WORLD_CUP_PERIOD_DATE_RANGES["geral"]


@pytest.mark.parametrize("key", list(WORLD_CUP_PERIOD_DATE_RANGES.keys()))
def test_form_returns_correct_dates_for_each_period(key):
    form = WorldCupRankingPeriodForm({"periodo": key})
    form.is_valid()
    assert form.get_period_dates() == WORLD_CUP_PERIOD_DATE_RANGES[key]


# ---------------------------------------------------------------------------
# GuessPool.get_ranking_for_world_cup_period tests
# ---------------------------------------------------------------------------


def test_ranking_ordered_by_score_descending():
    guesser_a = baker.make("core.Guesser")
    guesser_b = baker.make("core.Guesser")
    pool = baker.make("core.GuessPool", owner=guesser_a, guessers=[guesser_a, guesser_b])

    start, end = WORLD_CUP_PERIOD_DATE_RANGES["geral"]
    baker.make("core.WorldCupRankingEntry", pool=pool, guesser=guesser_a, start_date=start, end_date=end, score=5)
    baker.make("core.WorldCupRankingEntry", pool=pool, guesser=guesser_b, start_date=start, end_date=end, score=10)

    entries = list(pool.get_ranking_for_world_cup_period(start, end))
    assert entries[0].id == guesser_b.id
    assert entries[1].id == guesser_a.id


def test_guesser_without_entry_appears_with_score_zero():
    guesser = baker.make("core.Guesser")
    pool = baker.make("core.GuessPool", owner=guesser, guessers=[guesser])

    start, end = WORLD_CUP_PERIOD_DATE_RANGES["geral"]
    entries = list(pool.get_ranking_for_world_cup_period(start, end))

    assert len(entries) == 1
    assert entries[0].score == 0


# ---------------------------------------------------------------------------
# Guess.update_related_rankings — WorldCupRankingEntry update flow
# ---------------------------------------------------------------------------


def _make_finished_match_on_date(match_date: date, competition, home_team, away_team):
    return baker.make(
        "core.Match",
        competition=competition,
        home_team=home_team,
        away_team=away_team,
        status="FT",
        home_goals=2,
        away_goals=1,
        date_time=timezone.make_aware(datetime(match_date.year, match_date.month, match_date.day, 20, 0)),
    )


def test_world_cup_ranking_entry_created_for_match_inside_copa_period():
    """A guess scored on a match inside a Copa period must create WorldCupRankingEntry entries."""
    guesser = baker.make("core.Guesser")
    competition = baker.make("core.Competition")
    home_team = baker.make("core.Team", competitions=[competition])
    away_team = baker.make("core.Team", competitions=[competition])
    pool = baker.make("core.GuessPool", owner=guesser, competitions=[competition])

    match_date = date(2026, 6, 15)  # falls in geral + rodada_1
    match = _make_finished_match_on_date(match_date, competition, home_team, away_team)

    guess = baker.make(
        "core.Guess",
        guesser=guesser,
        match=match,
        home_goals=2,
        away_goals=1,
        score=0,
        consolidated=False,
    )
    pool.guesses.add(guess)

    guess.evaluate_and_consolidate()

    expected_periods = [
        (k, v) for k, v in WORLD_CUP_PERIOD_DATE_RANGES.items()
        if v[0] <= match_date <= v[1]
    ]
    assert len(expected_periods) > 0, "Test date must fall in at least one Copa period"

    for key, (start, end) in expected_periods:
        assert WorldCupRankingEntry.objects.filter(
            pool=pool,
            guesser=guesser,
            start_date=start,
            end_date=end,
        ).exists(), f"Missing WorldCupRankingEntry for period '{key}'"


def test_world_cup_ranking_entry_not_created_for_match_outside_copa_period():
    """A guess on a match outside all Copa date ranges must not create any WorldCupRankingEntry."""
    guesser = baker.make("core.Guesser")
    competition = baker.make("core.Competition")
    home_team = baker.make("core.Team", competitions=[competition])
    away_team = baker.make("core.Team", competitions=[competition])
    pool = baker.make("core.GuessPool", owner=guesser, competitions=[competition])

    match_date = date(2026, 5, 1)  # outside all Copa periods
    match = _make_finished_match_on_date(match_date, competition, home_team, away_team)

    guess = baker.make(
        "core.Guess",
        guesser=guesser,
        match=match,
        home_goals=2,
        away_goals=1,
        score=0,
        consolidated=False,
    )
    pool.guesses.add(guess)

    guess.evaluate_and_consolidate()

    assert WorldCupRankingEntry.objects.filter(pool=pool, guesser=guesser).count() == 0


# ---------------------------------------------------------------------------
# View tests
# ---------------------------------------------------------------------------


@override_settings(STATICFILES_STORAGE="django.contrib.staticfiles.storage.StaticFilesStorage")
@patch("core.views.timezone")
def test_world_cup_ranking_view_returns_200_inside_period(mock_tz, client):
    mock_tz.localdate.return_value = INSIDE_PERIOD

    guesser = baker.make("core.Guesser")
    pool = baker.make("core.GuessPool", owner=guesser, guessers=[guesser])

    client.force_login(guesser.user)
    response = client.get(reverse(URL_NAME, kwargs={"pool_slug": pool.slug}))

    assert response.status_code == 200


@override_settings(STATICFILES_STORAGE="django.contrib.staticfiles.storage.StaticFilesStorage")
@patch("core.views.timezone")
def test_world_cup_ranking_view_redirects_outside_period(mock_tz, client):
    mock_tz.localdate.return_value = OUTSIDE_PERIOD

    guesser = baker.make("core.Guesser")
    pool = baker.make("core.GuessPool", owner=guesser, guessers=[guesser])

    client.force_login(guesser.user)
    response = client.get(reverse(URL_NAME, kwargs={"pool_slug": pool.slug}))

    assert response.status_code == 302


@override_settings(STATICFILES_STORAGE="django.contrib.staticfiles.storage.StaticFilesStorage")
@patch("core.views.timezone")
def test_world_cup_ranking_view_redirects_when_no_guessers(mock_tz, client):
    mock_tz.localdate.return_value = INSIDE_PERIOD

    owner = baker.make("core.Guesser")
    pool = baker.make("core.GuessPool", owner=owner)
    pool.guessers.clear()

    client.force_login(owner.user)
    response = client.get(reverse(URL_NAME, kwargs={"pool_slug": pool.slug}))

    assert response.status_code == 302


@override_settings(STATICFILES_STORAGE="django.contrib.staticfiles.storage.StaticFilesStorage")
@patch("core.views.timezone")
def test_world_cup_ranking_view_shows_correct_scores_for_phase(mock_tz, client):
    mock_tz.localdate.return_value = INSIDE_PERIOD

    guesser_a = baker.make("core.Guesser")
    guesser_b = baker.make("core.Guesser")
    pool = baker.make("core.GuessPool", owner=guesser_a, guessers=[guesser_a, guesser_b])

    start, end = WORLD_CUP_PERIOD_DATE_RANGES["rodada_1"]
    baker.make("core.WorldCupRankingEntry", pool=pool, guesser=guesser_a, start_date=start, end_date=end, score=7)
    baker.make("core.WorldCupRankingEntry", pool=pool, guesser=guesser_b, start_date=start, end_date=end, score=3)

    client.force_login(guesser_a.user)
    response = client.get(
        reverse(URL_NAME, kwargs={"pool_slug": pool.slug}),
        {"periodo": "rodada_1"},
    )

    assert response.status_code == 200
    entries = list(response.context["ranking_entries"])
    assert entries[0].id == guesser_a.id
    assert entries[0].score == 7
    assert entries[1].id == guesser_b.id
    assert entries[1].score == 3
