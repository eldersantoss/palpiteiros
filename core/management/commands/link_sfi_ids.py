"""
Management command to populate sfi_id fields on Competition and Team models
by fuzzy-matching their names against data extracted from the Soccer Football
Info (SFI) API.

The matching uses rapidfuzz.fuzz.token_sort_ratio, which handles word-order
differences (e.g. "Brazil Serie A" ↔ "Serie A") and is case-insensitive.
Names are additionally normalized (Unicode NFKD + ASCII folding) before
comparison.

Usage examples:
    # Dry-run — preview matches without touching the DB and with custom a custom threshold (default is 70)
    python manage.py link_sfi_ids --json-file /path/to/data.json --threshold 85

    # Persisting IDs in DB (default threshold)
    python manage.py link_sfi_ids --json-file /path/to/data.json --apply-changes
"""

import json
import logging
import unicodedata
from pathlib import Path

from django.core.management.base import BaseCommand, CommandParser
from rapidfuzz import fuzz
from rapidfuzz import process as rf_process

from core.models import Competition, Team

logger = logging.getLogger(__name__)


_SFI_PREFIXES_TO_STRIP = ("brazil ", "brazil campeonato", "copa ", "uefa ")


def _normalize(text: str) -> str:
    """Return a lowercase, accent-stripped version of *text* for fuzzy comparison.

    Unicode NFKD decomposition splits accented characters into base character +
    combining mark; the ASCII encoding step then discards the combining marks,
    effectively removing accents (e.g. "Grêmio" → "gremio").
    """
    nfkd = unicodedata.normalize("NFKD", text)
    ascii_bytes = nfkd.encode("ascii", errors="ignore")
    return ascii_bytes.decode("ascii").lower().strip()


def _candidate_names(sfi_name: str) -> list[str]:
    """Return *sfi_name* plus prefix-stripped variants to widen the search surface."""
    normalized = _normalize(sfi_name)
    candidates = [normalized]
    for prefix in _SFI_PREFIXES_TO_STRIP:
        if normalized.startswith(prefix):
            candidates.append(normalized[len(prefix) :].strip())
    return candidates


def _best_match(
    candidates: list[str],
    choices_map: dict[str, object],
    threshold: float,
) -> tuple[object | None, float]:
    """Find the best fuzzy match for any of *candidates* in *choices_map*.

    Args:
        candidates: One or more normalized query strings (original + stripped variants).
        choices_map: Mapping of normalized name → model instance.
        threshold: Minimum score (0–100) to accept a match.

    Returns:
        A ``(instance, score)`` tuple, or ``(None, 0)`` when no match passes
        the threshold.
    """
    best_instance = None
    best_score = 0.0

    # rapidfuzz.process.extractOne uses WRatio by default; token_sort_ratio is
    # better for our use-case because it ignores word order.
    for candidate in candidates:
        result = rf_process.extractOne(
            candidate,
            choices=list(choices_map.keys()),
            scorer=fuzz.token_sort_ratio,
            score_cutoff=threshold,
        )
        if result is not None:
            matched_name, score, _ = result
            if score > best_score:
                best_score = score
                best_instance = choices_map[matched_name]

    return best_instance, best_score


class Command(BaseCommand):
    help = (
        "Populate sfi_id on Competition and Team models by fuzzy-matching "
        "their names against a JSON file extracted from the SFI API."
    )

    def add_arguments(self, parser: CommandParser) -> None:
        parser.add_argument(
            "--json-file",
            type=Path,
            help="Path to the file containing IDs of the championships and teams from Soccer Football Info",
        )
        parser.add_argument(
            "--threshold",
            type=float,
            default=70.0,
            help=(
                "Minimum rapidfuzz similarity score (0–100) required to accept "
                "a name match. Lower values allow more lenient matching. Defaults to 80."
            ),
        )
        parser.add_argument(
            "--apply-changes",
            action="store_true",
            default=False,
            help="Applies the changes to the database.",
        )

    def handle(self, *args, **options) -> None:
        """Entry point for the management command."""
        json_file: Path = options["json_file"]
        threshold: float = options["threshold"]
        apply_changes: bool = options["apply_changes"]

        if not json_file.exists():
            self.stderr.write(self.style.ERROR(f"JSON file not found: {json_file}"))
            return

        with json_file.open(encoding="utf-8") as fh:
            sfi_championships: list[dict] = json.load(fh)

        self.stdout.write(f"Loaded {len(sfi_championships)} SFI championships from {json_file}.")

        if not apply_changes:
            self.stdout.write(self.style.WARNING("DRY RUN — no database changes will be made.\n"))

        all_competitions = list(Competition.objects.all())
        all_teams = list(Team.objects.prefetch_related("competitions").all())

        competition_choices: dict[str, Competition] = {_normalize(c.name): c for c in all_competitions}
        all_team_choices: dict[str, Team] = {_normalize(t.name): t for t in all_teams}

        competition_updates: dict[int, str] = {}
        team_updates: dict[int, str] = {}

        unmatched_competitions: list[str] = []
        unmatched_teams: list[tuple[str, str]] = []

        for sfi_champ in sfi_championships:
            sfi_comp_name: str = sfi_champ["name"]
            sfi_comp_id: str = sfi_champ["id"]
            sfi_teams: list[dict] = sfi_champ.get("teams", [])

            comp_candidates = _candidate_names(sfi_comp_name)
            matched_comp, comp_score = _best_match(comp_candidates, competition_choices, threshold)

            if matched_comp is None:
                self.stdout.write(f"  [COMP] NO MATCH  SFI: {sfi_comp_name!r:<45}")
                unmatched_competitions.append(sfi_comp_name)
            else:
                self.stdout.write(f"  [COMP] {comp_score:5.1f}  SFI: {sfi_comp_name!r:<45}  DB: {matched_comp.name!r}")
                # Guard against overwriting an already-assigned sfi_id with a
                # different value (would indicate a duplicate/ambiguous match).
                if matched_comp.pk not in competition_updates:
                    competition_updates[matched_comp.pk] = sfi_comp_id

            if not sfi_teams:
                continue

            # Build a team choices map scoped to this competition so that, for
            # example, "Botafogo" matches the RJ club when processing Carioca
            # and "Botafogo SP" when processing Paulista.
            if matched_comp is not None:
                scoped_team_choices: dict[str, Team] = {_normalize(t.name): t for t in matched_comp.teams.all()}
            else:
                # Fallback to all teams when the competition couldn't be matched.
                scoped_team_choices = all_team_choices

            for sfi_team in sfi_teams:
                sfi_team_name: str = sfi_team["name"]
                sfi_team_id: str = sfi_team["id"]

                team_candidates = _candidate_names(sfi_team_name)
                matched_team, team_score = _best_match(team_candidates, scoped_team_choices, threshold)

                if matched_team is None:
                    self.stdout.write(f"    [TEAM] NO MATCH  SFI: {sfi_team_name!r}")
                    unmatched_teams.append((sfi_comp_name, sfi_team_name))
                else:
                    self.stdout.write(
                        f"    [TEAM] {team_score:5.1f}  SFI: {sfi_team_name!r:<40}  DB: {matched_team.name!r}"
                    )
                    if matched_team.pk not in team_updates:
                        team_updates[matched_team.pk] = sfi_team_id

        self.stdout.write("\n" + "─" * 70)
        self.stdout.write(
            f"Competitions: {len(competition_updates)} matched, " f"{len(unmatched_competitions)} unmatched."
        )
        self.stdout.write(f"Teams:        {len(team_updates)} matched, " f"{len(unmatched_teams)} unmatched.")

        if unmatched_competitions:
            self.stdout.write(self.style.WARNING("\nUnmatched competitions:"))
            for name in unmatched_competitions:
                self.stdout.write(f"  - {name}")

        if unmatched_teams:
            self.stdout.write(self.style.WARNING("\nUnmatched teams:"))
            for champ_name, team_name in unmatched_teams:
                self.stdout.write(f"  - [{champ_name}] {team_name}")

        if not apply_changes:
            self.stdout.write(self.style.WARNING("\nDRY RUN complete — no changes written."))
            return

        self._bulk_update_sfi_ids(competition_updates, team_updates)

        logger.info(
            "link_sfi_ids: updated %d competitions and %d teams with SFI IDs.",
            len(competition_updates),
            len(team_updates),
        )
        self.stdout.write(self.style.SUCCESS("\nDone. sfi_id fields updated successfully."))

    def _bulk_update_sfi_ids(
        self,
        competition_updates: dict[int, str],
        team_updates: dict[int, str],
    ) -> None:
        """Apply sfi_id assignments to the DB using bulk_update for efficiency."""
        if competition_updates:
            comps_to_update = Competition.objects.filter(pk__in=competition_updates.keys())
            for comp in comps_to_update:
                comp.sfi_id = competition_updates[comp.pk]
            Competition.objects.bulk_update(comps_to_update, ["sfi_id"])
            self.stdout.write(f"Updated {len(competition_updates)} competition(s).")

        if team_updates:
            teams_to_update = Team.objects.filter(pk__in=team_updates.keys())
            for team in teams_to_update:
                team.sfi_id = team_updates[team.pk]
            Team.objects.bulk_update(teams_to_update, ["sfi_id"])
            self.stdout.write(f"Updated {len(team_updates)} team(s).")
