import pytest
from django.db.models import Q
from model_bakery import baker

from core.models import CompetitionGroup, GroupStanding


pytestmark = pytest.mark.django_db


def _make_finished_match(competition, home, away, hg, ag, hyc=0, ayc=0, hrc=0, arc=0):
    match = baker.make(
        "core.Match",
        competition=competition,
        home_team=home,
        away_team=away,
        status="FT",
        home_goals=hg,
        away_goals=ag,
        home_yellow_cards=hyc,
        away_yellow_cards=ayc,
        home_red_cards=hrc,
        away_red_cards=arc,
    )

    groups = CompetitionGroup.objects.filter(competition=competition).filter(Q(teams=home) | Q(teams=away)).distinct()
    for group in groups:
        group.recalculate_standings()
    return match


def test_get_standings_empty_when_no_teams():
    competition = baker.make("core.Competition")
    group = baker.make("core.CompetitionGroup", competition=competition)

    assert group.get_standings() == []


def test_get_standings_empty_when_no_finished_matches():
    competition = baker.make("core.Competition")
    home = baker.make("core.Team")
    away = baker.make("core.Team")
    group = baker.make("core.CompetitionGroup", competition=competition)
    group.teams.set([home, away])

    baker.make(
        "core.Match",
        competition=competition,
        home_team=home,
        away_team=away,
        status="NS",
        home_goals=None,
        away_goals=None,
    )

    standings = group.get_standings()
    assert all(entry["pj"] == 0 for entry in standings)
    assert all(entry["pts"] == 0 for entry in standings)


def test_get_standings_victory_gives_3_points():
    competition = baker.make("core.Competition")
    home = baker.make("core.Team")
    away = baker.make("core.Team")
    group = baker.make("core.CompetitionGroup", competition=competition)
    group.teams.set([home, away])

    _make_finished_match(competition, home, away, hg=2, ag=0)

    standings = group.get_standings()
    home_entry = next(e for e in standings if e["team"] == home)
    away_entry = next(e for e in standings if e["team"] == away)

    assert home_entry["pts"] == 3
    assert away_entry["pts"] == 0


def test_get_standings_draw_gives_1_point_each():
    competition = baker.make("core.Competition")
    home = baker.make("core.Team")
    away = baker.make("core.Team")
    group = baker.make("core.CompetitionGroup", competition=competition)
    group.teams.set([home, away])

    _make_finished_match(competition, home, away, hg=1, ag=1)

    standings = group.get_standings()
    for entry in standings:
        assert entry["pts"] == 1


def test_get_standings_goal_counts():
    competition = baker.make("core.Competition")
    home = baker.make("core.Team")
    away = baker.make("core.Team")
    group = baker.make("core.CompetitionGroup", competition=competition)
    group.teams.set([home, away])

    _make_finished_match(competition, home, away, hg=3, ag=1)

    standings = group.get_standings()
    home_entry = next(e for e in standings if e["team"] == home)
    away_entry = next(e for e in standings if e["team"] == away)

    assert home_entry["gf"] == 3
    assert home_entry["ga"] == 1
    assert away_entry["gf"] == 1
    assert away_entry["ga"] == 3


def test_get_standings_card_counts():
    competition = baker.make("core.Competition")
    home = baker.make("core.Team")
    away = baker.make("core.Team")
    group = baker.make("core.CompetitionGroup", competition=competition)
    group.teams.set([home, away])

    _make_finished_match(competition, home, away, hg=1, ag=0, hyc=2, ayc=3, hrc=0, arc=1)

    standings = group.get_standings()
    home_entry = next(e for e in standings if e["team"] == home)
    away_entry = next(e for e in standings if e["team"] == away)

    assert home_entry["yc"] == 2
    assert home_entry["rc"] == 0
    assert away_entry["yc"] == 3
    assert away_entry["rc"] == 1


def test_get_standings_ordering_by_points():
    competition = baker.make("core.Competition")
    team_a = baker.make("core.Team")
    team_b = baker.make("core.Team")
    team_c = baker.make("core.Team")
    group = baker.make("core.CompetitionGroup", competition=competition)
    group.teams.set([team_a, team_b, team_c])

    _make_finished_match(competition, team_a, team_b, hg=1, ag=0)  # A: 3pts, B: 0pts
    _make_finished_match(competition, team_c, team_b, hg=1, ag=1)  # C: 1pt, B: 1pt

    standings = group.get_standings()
    assert standings[0]["team"] == team_a
    assert standings[0]["pts"] == 3


def test_get_standings_tiebreak_by_goal_difference():
    competition = baker.make("core.Competition")
    team_a = baker.make("core.Team")
    team_b = baker.make("core.Team")
    team_c = baker.make("core.Team")
    group = baker.make("core.CompetitionGroup", competition=competition)
    group.teams.set([team_a, team_b, team_c])

    # Both A and B get 3pts but A has better goal diff (+2 vs +1)
    _make_finished_match(competition, team_a, team_c, hg=3, ag=1)  # A: 3pts, saldo +2
    _make_finished_match(competition, team_b, team_c, hg=2, ag=1)  # B: 3pts, saldo +1

    standings = group.get_standings()
    assert standings[0]["team"] == team_a
    assert standings[1]["team"] == team_b


def test_get_standings_tiebreak_by_goals_scored():
    competition = baker.make("core.Competition")
    team_a = baker.make("core.Team")
    team_b = baker.make("core.Team")
    team_c = baker.make("core.Team")
    group = baker.make("core.CompetitionGroup", competition=competition)
    group.teams.set([team_a, team_b, team_c])

    # A and B: same pts (3), same goal diff (+1), but A scored more
    _make_finished_match(competition, team_a, team_c, hg=2, ag=1)  # A: 3pts, gf=2, saldo +1
    _make_finished_match(competition, team_b, team_c, hg=1, ag=0)  # B: 3pts, gf=1, saldo +1

    standings = group.get_standings()
    assert standings[0]["team"] == team_a
    assert standings[1]["team"] == team_b


def test_get_standings_tiebreak_by_yellow_cards():
    competition = baker.make("core.Competition")
    team_a = baker.make("core.Team")
    team_b = baker.make("core.Team")
    team_c = baker.make("core.Team")
    group = baker.make("core.CompetitionGroup", competition=competition)
    group.teams.set([team_a, team_b, team_c])

    # Same pts, same goal diff, same goals scored; A has fewer yellow cards
    _make_finished_match(competition, team_a, team_c, hg=1, ag=0, hyc=1)
    _make_finished_match(competition, team_b, team_c, hg=1, ag=0, hyc=2)

    standings = group.get_standings()
    assert standings[0]["team"] == team_a
    assert standings[1]["team"] == team_b


def test_get_standings_tiebreak_by_red_cards():
    competition = baker.make("core.Competition")
    team_a = baker.make("core.Team")
    team_b = baker.make("core.Team")
    team_c = baker.make("core.Team")
    group = baker.make("core.CompetitionGroup", competition=competition)
    group.teams.set([team_a, team_b, team_c])

    # Same pts, same goal diff, same goals, same yellow; A has fewer red cards
    _make_finished_match(competition, team_a, team_c, hg=1, ag=0, hyc=1, hrc=0)
    _make_finished_match(competition, team_b, team_c, hg=1, ag=0, hyc=1, hrc=1)

    standings = group.get_standings()
    assert standings[0]["team"] == team_a
    assert standings[1]["team"] == team_b


def test_get_standings_ignores_matches_of_other_competitions():
    competition = baker.make("core.Competition")
    other_competition = baker.make("core.Competition")
    home = baker.make("core.Team")
    away = baker.make("core.Team")
    group = baker.make("core.CompetitionGroup", competition=competition)
    group.teams.set([home, away])

    # Match from another competition should not affect standings
    _make_finished_match(other_competition, home, away, hg=5, ag=0)

    standings = group.get_standings()
    assert all(entry["pts"] == 0 for entry in standings)
    assert all(entry["pj"] == 0 for entry in standings)


def test_get_standings_batch_equals_individual():
    """get_standings_batch() must produce the same results as calling
    get_standings() individually for each group."""
    competition = baker.make("core.Competition")
    team_a1 = baker.make("core.Team")
    team_a2 = baker.make("core.Team")
    team_b1 = baker.make("core.Team")
    team_b2 = baker.make("core.Team")

    group_a = baker.make("core.CompetitionGroup", competition=competition, name="Grupo A")
    group_a.teams.set([team_a1, team_a2])
    group_b = baker.make("core.CompetitionGroup", competition=competition, name="Grupo B")
    group_b.teams.set([team_b1, team_b2])

    _make_finished_match(competition, team_a1, team_a2, hg=2, ag=1)
    _make_finished_match(competition, team_b1, team_b2, hg=0, ag=0)

    # Individual results
    individual_a = group_a.get_standings()
    individual_b = group_b.get_standings()

    # Batch results
    batch_results = CompetitionGroup.get_standings_batch([group_a, group_b])

    # Sort results using a stable key to handle tie-breakers deterministically in the test comparison
    def sort_key(item):
        return (-item["pts"], -(item["gf"] - item["ga"]), -item["gf"], item["yc"], item["rc"], item["team"].id)

    individual_a = sorted(individual_a, key=sort_key)
    batch_a = sorted(batch_results[group_a.id], key=sort_key)
    individual_b = sorted(individual_b, key=sort_key)
    batch_b = sorted(batch_results[group_b.id], key=sort_key)

    # Compare group A
    assert len(batch_a) == len(individual_a)
    for ind, bat in zip(individual_a, batch_a):
        assert ind["team"] == bat["team"]
        assert ind["pts"] == bat["pts"]
        assert ind["pj"] == bat["pj"]
        assert ind["gf"] == bat["gf"]
        assert ind["ga"] == bat["ga"]
        assert ind["yc"] == bat["yc"]
        assert ind["rc"] == bat["rc"]

    # Compare group B
    assert len(batch_b) == len(individual_b)
    for ind, bat in zip(individual_b, batch_b):
        assert ind["team"] == bat["team"]
        assert ind["pts"] == bat["pts"]


def test_get_standings_batch_empty_group():
    """get_standings_batch() with a group that has no teams returns an empty list."""
    competition = baker.make("core.Competition")
    empty_group = baker.make("core.CompetitionGroup", competition=competition, name="Empty")

    results = CompetitionGroup.get_standings_batch([empty_group])
    assert results[empty_group.id] == []


def test_recalculate_standings_creates_and_updates_database_records():
    competition = baker.make("core.Competition")
    home = baker.make("core.Team")
    away = baker.make("core.Team")
    group = baker.make("core.CompetitionGroup", competition=competition)
    group.teams.set([home, away])

    # Direct creation without triggering helper
    baker.make(
        "core.Match",
        competition=competition,
        home_team=home,
        away_team=away,
        status="FT",
        home_goals=2,
        away_goals=1,
        home_yellow_cards=1,
        away_yellow_cards=2,
        home_red_cards=0,
        away_red_cards=1,
    )

    group.recalculate_standings()

    home_standing = GroupStanding.objects.get(group=group, team=home)
    away_standing = GroupStanding.objects.get(group=group, team=away)

    assert home_standing.pts == 3
    assert home_standing.pj == 1
    assert home_standing.gf == 2
    assert home_standing.ga == 1
    assert home_standing.gd == 1
    assert home_standing.yc == 1
    assert home_standing.rc == 0

    assert away_standing.pts == 0
    assert away_standing.pj == 1
    assert away_standing.gf == 1
    assert away_standing.ga == 2
    assert away_standing.gd == -1
    assert away_standing.yc == 2
    assert away_standing.rc == 1


def test_recalculate_standings_zeroes_teams_with_no_matches():
    competition = baker.make("core.Competition")
    home = baker.make("core.Team")
    away = baker.make("core.Team")
    group = baker.make("core.CompetitionGroup", competition=competition)
    group.teams.set([home, away])

    # No matches played at all
    group.recalculate_standings()

    home_standing = GroupStanding.objects.get(group=group, team=home)
    assert home_standing.pts == 0
    assert home_standing.pj == 0


def test_recalculate_standings_removes_deleted_group_teams():
    competition = baker.make("core.Competition")
    home = baker.make("core.Team")
    away = baker.make("core.Team")
    group = baker.make("core.CompetitionGroup", competition=competition)
    group.teams.set([home, away])

    group.recalculate_standings()
    assert GroupStanding.objects.filter(group=group).count() == 2

    # Remove away team
    group.teams.set([home])
    # Calling recalculate should clean up the GroupStanding for away team
    group.recalculate_standings()

    assert GroupStanding.objects.filter(group=group).count() == 1
    assert GroupStanding.objects.filter(group=group, team=home).exists()
    assert not GroupStanding.objects.filter(group=group, team=away).exists()


def test_group_teams_m2m_changed_signal_triggers_recalculation():
    competition = baker.make("core.Competition")
    home = baker.make("core.Team")
    away = baker.make("core.Team")
    group = baker.make("core.CompetitionGroup", competition=competition)

    # Initial state: 0 teams
    assert GroupStanding.objects.filter(group=group).count() == 0

    # Setting teams via relation triggers signal post_add/post_clear etc.
    group.teams.set([home, away])

    # Since the signal fired, entries should exist immediately without manual recalculation
    assert GroupStanding.objects.filter(group=group).count() == 2
    assert GroupStanding.objects.filter(group=group, team=home).exists()


def test_get_standings_batch_fallback_when_group_standings_table_is_empty():
    competition = baker.make("core.Competition")
    home = baker.make("core.Team")
    away = baker.make("core.Team")
    group = baker.make("core.CompetitionGroup", competition=competition)
    group.teams.set([home, away])

    # Clear GroupStanding entries for the group to simulate empty DB / cache state
    GroupStanding.objects.filter(group=group).delete()
    assert GroupStanding.objects.filter(group=group).count() == 0

    # Call get_standings_batch
    results = CompetitionGroup.get_standings_batch([group])

    # It should have triggered fallback recalculation
    assert GroupStanding.objects.filter(group=group).count() == 2
    assert len(results[group.id]) == 2
