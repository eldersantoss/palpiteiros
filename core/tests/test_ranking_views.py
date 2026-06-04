from datetime import date, datetime
from unittest.mock import patch

import pytest
from django.test import override_settings
from django.urls import reverse
from django.utils import timezone
from model_bakery import baker

from core.models import Match, RankingEntry

pytestmark = pytest.mark.django_db


@override_settings(STATICFILES_STORAGE="django.contrib.staticfiles.storage.StaticFilesStorage")
@patch("core.management.commands.sync_matches_sfi.django_timezone")
@patch("requests.get")
def test_ranking_view_shows_updated_score_after_sync(
    mock_get,
    mock_tz,
    mock_success_response,
    get_sfi_matches_by_day_past_response,
    sfi_competition_id,
    sfi_home_team_id,
    sfi_away_team_id,
    client,
):
    """Ranking page must show updated score after match sync, without extra page visits."""
    mock_tz.now.return_value.date.return_value = date(2026, 3, 3)
    mock_tz.timedelta = timezone.timedelta

    competition = baker.make("core.Competition", sfi_id=sfi_competition_id)
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

    from django.core.management import call_command

    call_command("sync_matches_sfi", date=date(2026, 2, 26))

    client.force_login(guesser.user)
    response = client.get(
        reverse("core:ranking", kwargs={"pool_slug": pool.slug}),
        {"periodo": "geral"},
    )

    assert response.status_code == 200

    row_for_guesser = next(entry for entry in response.context["ranking_entries"] if entry.id == guesser.id)
    assert row_for_guesser.score == 10


@override_settings(STATICFILES_STORAGE="django.contrib.staticfiles.storage.StaticFilesStorage")
def test_guesses_by_period_get_does_not_write_scores(client):
    """Rendering guesses-by-period should not trigger score consolidation side effects."""
    guesser = baker.make("core.Guesser")
    competition = baker.make("core.Competition")
    home_team = baker.make("core.Team", competitions=[competition])
    away_team = baker.make("core.Team", competitions=[competition])
    pool = baker.make("core.GuessPool", owner=guesser, competitions=[competition])

    finished_match = baker.make(
        "core.Match",
        competition=competition,
        home_team=home_team,
        away_team=away_team,
        status=Match.FINSHED,
        home_goals=3,
        away_goals=1,
        date_time=timezone.now() - timezone.timedelta(hours=2),
    )
    guess = baker.make(
        "core.Guess",
        guesser=guesser,
        match=finished_match,
        home_goals=3,
        away_goals=1,
        score=0,
        consolidated=False,
    )
    pool.guesses.add(guess)

    client.force_login(guesser.user)
    response = client.get(
        reverse("core:guesses_by_period", kwargs={"pool_slug": pool.slug}),
        {"periodo": "geral", "palpiteiro": str(guesser.id)},
    )

    assert response.status_code == 200

    guess.refresh_from_db()
    assert guess.consolidated is False
    assert guess.score == 0
    assert RankingEntry.objects.filter(pool=pool, guesser=guesser).count() == 0
