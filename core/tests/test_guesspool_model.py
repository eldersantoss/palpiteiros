import pytest
from model_bakery import baker

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
