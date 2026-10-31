from datetime import date, datetime
from unittest.mock import patch

import pytest
from django.test import override_settings
from django.urls import reverse
from django.utils import timezone
from model_bakery import baker

from core.constants import WORLD_CUP_PERIOD_DATE_RANGES
from core.forms import WorldCupGuessesPeriodForm

pytestmark = pytest.mark.django_db

URL_NAME = "core:world_cup_guesses_by_period"
INSIDE_PERIOD = date(2026, 6, 15)
OUTSIDE_PERIOD = date(2026, 5, 1)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_aware(d: date, hour: int = 20) -> datetime:
    return timezone.make_aware(datetime(d.year, d.month, d.day, hour, 0))


def _make_pool(*guessers):
    owner = guessers[0]
    pool = baker.make("core.GuessPool", owner=owner, guessers=list(guessers))
    return pool


def _make_finished_match(match_date: date):
    competition = baker.make("core.Competition")
    home_team = baker.make("core.Team", competitions=[competition])
    away_team = baker.make("core.Team", competitions=[competition])
    return baker.make(
        "core.Match",
        competition=competition,
        home_team=home_team,
        away_team=away_team,
        status="FT",
        home_goals=2,
        away_goals=1,
        date_time=_make_aware(match_date),
    )


def _make_future_match(match_date: date):
    competition = baker.make("core.Competition")
    home_team = baker.make("core.Team", competitions=[competition])
    away_team = baker.make("core.Team", competitions=[competition])
    return baker.make(
        "core.Match",
        competition=competition,
        home_team=home_team,
        away_team=away_team,
        status="NS",
        home_goals=None,
        away_goals=None,
        date_time=_make_aware(match_date),
    )


def _make_guess(guesser, match, pool, home_goals=2, away_goals=1, score=10):
    guess = baker.make(
        "core.Guess",
        guesser=guesser,
        match=match,
        home_goals=home_goals,
        away_goals=away_goals,
        score=score,
        consolidated=True,
    )
    pool.guesses.add(guess)
    return guess


# ---------------------------------------------------------------------------
# Form tests
# ---------------------------------------------------------------------------


def test_form_default_returns_geral_dates():
    pool = baker.make("core.GuessPool")
    form = WorldCupGuessesPeriodForm({}, pool=pool)
    form.is_valid()
    assert form.get_period_dates() == WORLD_CUP_PERIOD_DATE_RANGES["geral"]


def test_form_empty_periodo_returns_geral_dates():
    pool = baker.make("core.GuessPool")
    form = WorldCupGuessesPeriodForm({"periodo": ""}, pool=pool)
    form.is_valid()
    assert form.get_period_dates() == WORLD_CUP_PERIOD_DATE_RANGES["geral"]


@pytest.mark.parametrize("key", list(WORLD_CUP_PERIOD_DATE_RANGES.keys()))
def test_form_returns_correct_dates_for_each_period(key):
    pool = baker.make("core.GuessPool")
    form = WorldCupGuessesPeriodForm({"periodo": key}, pool=pool)
    form.is_valid()
    assert form.get_period_dates() == WORLD_CUP_PERIOD_DATE_RANGES[key]


def test_form_palpiteiro_choices_match_pool_guessers():
    guesser_a = baker.make("core.Guesser")
    guesser_b = baker.make("core.Guesser")
    pool = _make_pool(guesser_a, guesser_b)

    form = WorldCupGuessesPeriodForm({}, pool=pool)
    choice_ids = [int(pk) for pk, _ in form.fields["palpiteiro"].choices]

    assert guesser_a.id in choice_ids
    assert guesser_b.id in choice_ids


def test_form_get_guesser_returns_selected_id():
    guesser = baker.make("core.Guesser")
    pool = _make_pool(guesser)

    form = WorldCupGuessesPeriodForm({"palpiteiro": str(guesser.id), "periodo": "geral"}, pool=pool)
    form.is_valid()
    assert str(form.get_guesser()) == str(guesser.id)


# ---------------------------------------------------------------------------
# View access / guard tests
# ---------------------------------------------------------------------------


@override_settings(STATICFILES_STORAGE="django.contrib.staticfiles.storage.StaticFilesStorage")
@patch("core.views.timezone")
def test_view_returns_200_inside_period(mock_tz, client):
    mock_tz.localdate.return_value = INSIDE_PERIOD
    mock_tz.localtime.return_value = _make_aware(INSIDE_PERIOD, hour=23)

    guesser = baker.make("core.Guesser")
    pool = _make_pool(guesser)

    client.force_login(guesser.user)
    response = client.get(reverse(URL_NAME, kwargs={"pool_slug": pool.slug}))

    assert response.status_code == 200


@override_settings(STATICFILES_STORAGE="django.contrib.staticfiles.storage.StaticFilesStorage")
@patch("core.views.timezone")
def test_view_redirects_outside_period(mock_tz, client):
    mock_tz.localdate.return_value = OUTSIDE_PERIOD

    guesser = baker.make("core.Guesser")
    pool = _make_pool(guesser)

    client.force_login(guesser.user)
    response = client.get(reverse(URL_NAME, kwargs={"pool_slug": pool.slug}))

    assert response.status_code == 302


@override_settings(STATICFILES_STORAGE="django.contrib.staticfiles.storage.StaticFilesStorage")
@patch("core.views.timezone")
def test_view_requires_login(mock_tz, client):
    mock_tz.localdate.return_value = INSIDE_PERIOD

    guesser = baker.make("core.Guesser")
    pool = _make_pool(guesser)

    response = client.get(reverse(URL_NAME, kwargs={"pool_slug": pool.slug}))

    assert response.status_code == 302


# ---------------------------------------------------------------------------
# View queryset / filtering tests
# ---------------------------------------------------------------------------


@override_settings(STATICFILES_STORAGE="django.contrib.staticfiles.storage.StaticFilesStorage")
@patch("core.views.timezone")
def test_view_shows_guesses_for_selected_guesser_and_period(mock_tz, client):
    """Only guesses from the selected guesser inside the selected period are shown."""
    mock_tz.localdate.return_value = INSIDE_PERIOD
    mock_tz.localtime.return_value = _make_aware(INSIDE_PERIOD, hour=23)

    guesser_a = baker.make("core.Guesser")
    guesser_b = baker.make("core.Guesser")
    pool = _make_pool(guesser_a, guesser_b)

    rodada1_start, rodada1_end = WORLD_CUP_PERIOD_DATE_RANGES["rodada_1"]
    match_in_period = _make_finished_match(rodada1_start)
    guess_a = _make_guess(guesser_a, match_in_period, pool)
    _make_guess(guesser_b, match_in_period, pool)

    client.force_login(guesser_a.user)
    response = client.get(
        reverse(URL_NAME, kwargs={"pool_slug": pool.slug}),
        {"palpiteiro": guesser_a.id, "periodo": "rodada_1"},
    )

    assert response.status_code == 200
    guesses = list(response.context["guesses"])
    assert len(guesses) == 1
    assert guesses[0].id == guess_a.id


@override_settings(STATICFILES_STORAGE="django.contrib.staticfiles.storage.StaticFilesStorage")
@patch("core.views.timezone")
def test_view_excludes_guesses_outside_selected_period(mock_tz, client):
    """Guesses from a different Copa period must not appear."""
    mock_tz.localdate.return_value = INSIDE_PERIOD
    mock_tz.localtime.return_value = _make_aware(INSIDE_PERIOD, hour=23)

    guesser = baker.make("core.Guesser")
    pool = _make_pool(guesser)

    rodada1_start, _ = WORLD_CUP_PERIOD_DATE_RANGES["rodada_1"]
    rodada2_start, _ = WORLD_CUP_PERIOD_DATE_RANGES["rodada_2"]

    match_r1 = _make_finished_match(rodada1_start)
    match_r2 = _make_finished_match(rodada2_start)
    _make_guess(guesser, match_r1, pool)
    _make_guess(guesser, match_r2, pool)

    client.force_login(guesser.user)
    response = client.get(
        reverse(URL_NAME, kwargs={"pool_slug": pool.slug}),
        {"palpiteiro": guesser.id, "periodo": "rodada_1"},
    )

    assert response.status_code == 200
    guesses = list(response.context["guesses"])
    match_ids = {g.match_id for g in guesses}
    assert match_r1.id in match_ids
    assert match_r2.id not in match_ids


@override_settings(STATICFILES_STORAGE="django.contrib.staticfiles.storage.StaticFilesStorage")
@patch("core.views.timezone")
def test_view_excludes_future_matches(mock_tz, client):
    """Matches that haven't started yet must not appear even if in the date range."""
    mock_tz.localdate.return_value = INSIDE_PERIOD

    guesser = baker.make("core.Guesser")
    pool = _make_pool(guesser)

    rodada1_start, _ = WORLD_CUP_PERIOD_DATE_RANGES["rodada_1"]
    future_match = _make_future_match(rodada1_start)
    _make_guess(guesser, future_match, pool)

    # localtime must be BEFORE the match so the filter kicks in
    mock_tz.localtime.return_value = _make_aware(rodada1_start, hour=0)

    client.force_login(guesser.user)
    response = client.get(
        reverse(URL_NAME, kwargs={"pool_slug": pool.slug}),
        {"palpiteiro": guesser.id, "periodo": "rodada_1"},
    )

    assert response.status_code == 200
    assert list(response.context["guesses"]) == []


@override_settings(STATICFILES_STORAGE="django.contrib.staticfiles.storage.StaticFilesStorage")
@patch("core.views.timezone")
def test_view_geral_period_shows_all_copa_guesses(mock_tz, client):
    """Período 'geral' must include guesses from any match inside the full Copa range."""
    geral_end = WORLD_CUP_PERIOD_DATE_RANGES["geral"][1]
    mock_tz.localdate.return_value = INSIDE_PERIOD
    # localtime must be after geral_end so both matches are treated as past
    mock_tz.localtime.return_value = _make_aware(geral_end, hour=23)

    guesser = baker.make("core.Guesser")
    pool = _make_pool(guesser)

    geral_start, geral_end = WORLD_CUP_PERIOD_DATE_RANGES["geral"]
    match_start = _make_finished_match(geral_start)
    match_end = _make_finished_match(geral_end)
    guess_start = _make_guess(guesser, match_start, pool)
    guess_end = _make_guess(guesser, match_end, pool)

    client.force_login(guesser.user)
    response = client.get(
        reverse(URL_NAME, kwargs={"pool_slug": pool.slug}),
        {"palpiteiro": guesser.id, "periodo": "geral"},
    )

    assert response.status_code == 200
    guess_ids = {g.id for g in response.context["guesses"]}
    assert guess_start.id in guess_ids
    assert guess_end.id in guess_ids


@override_settings(STATICFILES_STORAGE="django.contrib.staticfiles.storage.StaticFilesStorage")
@patch("core.views.timezone")
def test_view_total_score_is_sum_of_displayed_guesses(mock_tz, client):
    """total_score in context must equal the sum of scores of displayed guesses."""
    mock_tz.localdate.return_value = INSIDE_PERIOD
    mock_tz.localtime.return_value = _make_aware(INSIDE_PERIOD, hour=23)

    guesser = baker.make("core.Guesser")
    pool = _make_pool(guesser)

    rodada1_start, _ = WORLD_CUP_PERIOD_DATE_RANGES["rodada_1"]
    match1 = _make_finished_match(rodada1_start)
    match2 = _make_finished_match(rodada1_start)
    _make_guess(guesser, match1, pool, score=7)
    _make_guess(guesser, match2, pool, score=3)

    client.force_login(guesser.user)
    response = client.get(
        reverse(URL_NAME, kwargs={"pool_slug": pool.slug}),
        {"palpiteiro": guesser.id, "periodo": "rodada_1"},
    )

    assert response.status_code == 200
    assert response.context["total_score"] == 10


@override_settings(STATICFILES_STORAGE="django.contrib.staticfiles.storage.StaticFilesStorage")
@patch("core.views.timezone")
def test_view_empty_when_no_guesses_in_period(mock_tz, client):
    """When no guesses exist for the period, guesses must be an empty queryset."""
    mock_tz.localdate.return_value = INSIDE_PERIOD
    mock_tz.localtime.return_value = _make_aware(INSIDE_PERIOD, hour=23)

    guesser = baker.make("core.Guesser")
    pool = _make_pool(guesser)

    client.force_login(guesser.user)
    response = client.get(
        reverse(URL_NAME, kwargs={"pool_slug": pool.slug}),
        {"palpiteiro": guesser.id, "periodo": "final"},
    )

    assert response.status_code == 200
    assert list(response.context["guesses"]) == []
    assert response.context["total_score"] == 0


@override_settings(STATICFILES_STORAGE="django.contrib.staticfiles.storage.StaticFilesStorage")
@patch("core.views.timezone")
def test_view_defaults_to_logged_in_guesser_when_no_params(mock_tz, client):
    """With no query params, the view defaults to the logged-in guesser."""
    mock_tz.localdate.return_value = INSIDE_PERIOD
    mock_tz.localtime.return_value = _make_aware(INSIDE_PERIOD, hour=23)

    guesser_a = baker.make("core.Guesser")
    guesser_b = baker.make("core.Guesser")
    pool = _make_pool(guesser_a, guesser_b)

    rodada1_start, _ = WORLD_CUP_PERIOD_DATE_RANGES["rodada_1"]
    match = _make_finished_match(rodada1_start)
    guess_a = _make_guess(guesser_a, match, pool)
    _make_guess(guesser_b, match, pool)

    client.force_login(guesser_a.user)
    # no GET params — should fall back to guesser_a + geral
    response = client.get(reverse(URL_NAME, kwargs={"pool_slug": pool.slug}))

    assert response.status_code == 200
    guess_ids = {g.id for g in response.context["guesses"]}
    assert guess_a.id in guess_ids


@override_settings(STATICFILES_STORAGE="django.contrib.staticfiles.storage.StaticFilesStorage")
@patch("core.views.timezone")
def test_view_performance_query_count(mock_tz, client, django_assert_num_queries):
    mock_tz.localdate.return_value = INSIDE_PERIOD
    mock_tz.localtime.return_value = _make_aware(INSIDE_PERIOD, hour=23)

    # Create 5 guessers
    guessers = [baker.make("core.Guesser") for _ in range(5)]
    pool = _make_pool(*guessers)

    # Create 5 finished matches and guesses
    rodada1_start, _ = WORLD_CUP_PERIOD_DATE_RANGES["rodada_1"]
    for _ in range(5):
        match = _make_finished_match(rodada1_start)
        _make_guess(guessers[0], match, pool)

    client.force_login(guessers[0].user)

    # With N+1 problems:
    # - 1 query for GuessPool
    # - 1 query checking guessers.contains()
    # - 1 query to fetch pool guessers for the form choice field
    # - 5 queries (1 per guesser) to fetch g.user inside form __init__
    # - 1 query to fetch guesses
    # - 1 query to fetch total score (Sum)
    # - 5 queries (1 per guess) to fetch guess.match
    # - 5 queries to fetch match.home_team
    # - 5 queries to fetch match.away_team
    # Total would be 25+ queries!
    # Let's assert a low number of queries (e.g. 7 queries) to fail initially.
    # The expected optimized query count is exactly 8 queries.
    with django_assert_num_queries(8):
        response = client.get(
            reverse(URL_NAME, kwargs={"pool_slug": pool.slug}),
            {"palpiteiro": guessers[0].id, "periodo": "rodada_1"},
        )
        assert response.status_code == 200

