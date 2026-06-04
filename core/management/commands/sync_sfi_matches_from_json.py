"""Management command: sync_sfi_matches_from_json.

Loads matches from a local JSON file (same structure as the SFI API response)
and upserts them into the database.

Expected JSON format:
    {"result": [ <match objects> ]}

Matches from competitions not registered with an SFI ID are silently skipped.
Teams not found for a tracked competition are created and linked automatically.
"""

import json
import logging
from datetime import datetime, timezone
from enum import StrEnum
from pathlib import Path

from django.core.management.base import BaseCommand, CommandParser

from core.models import Competition, Match, Team
from core.services.sfi import SFIMatch, SFIService

logger = logging.getLogger(__name__)


class ProcessMatchResult(StrEnum):
    created = "created"
    updated = "updated"
    skipped = "skipped"


class Command(BaseCommand):
    """Create and update matches from a local SFI-format JSON file."""

    help = (
        "Reads matches from a local JSON file (SFI API format) and creates or "
        "updates them in the database."
    )

    def add_arguments(self, parser: CommandParser) -> None:
        parser.add_argument(
            "file",
            type=Path,
            help="Path to the JSON file containing match data.",
        )

    def handle(self, *args, **options) -> None:
        competitions_by_sfi_id = {
            comp.sfi_id: comp for comp in Competition.objects.filter(sfi_id__isnull=False) if comp.sfi_id is not None
        }

        if not competitions_by_sfi_id:
            self.stdout.write("No competitions with an SFI ID are registered. Aborting.")
            return

        file_path: Path = options["file"]

        try:
            matches = self._load_matches(file_path)
        except Exception:
            logger.exception("Failed to load matches from %s.", file_path)
            self.stderr.write(f"ERROR: could not read or parse '{file_path}'.")
            return

        self.stdout.write(f"sync_sfi_matches_from_json: processing {len(matches)} match(es) from '{file_path}'")

        created, updated, skipped, teams_created = 0, 0, 0, 0

        for match in matches:
            outcome, created_teams_for_match = self._process_match(match, competitions_by_sfi_id)
            teams_created += created_teams_for_match

            if outcome == ProcessMatchResult.created:
                created += 1
            elif outcome == ProcessMatchResult.updated:
                updated += 1
            else:
                skipped += 1

        self.stdout.write(
            f"Done: {created} created, {updated} updated, {skipped} skipped, "
            f"{teams_created} teams registered."
        )

    def _load_matches(self, file_path: Path) -> list[SFIMatch]:
        with file_path.open(encoding="utf-8") as f:
            data = json.load(f)
        return data.get("result", [])

    def _process_match(
        self,
        match: SFIMatch,
        competitions_by_sfi_id: dict[str, Competition],
    ) -> tuple[ProcessMatchResult, int]:
        competition = competitions_by_sfi_id.get(match["championship"]["id"])
        if competition is None:
            return ProcessMatchResult.skipped, 0

        status = match["status"]

        if status not in SFIService.SFI_MATCH_STATUSES:
            logger.warning("Skipping match %s with unhandled status '%s'.", match["id"], status)
            return ProcessMatchResult.skipped, 0

        home_team, home_team_created = self._get_or_create_competition_team(
            match_id=match["id"],
            side="home",
            team_sfi_id=match["teamA"]["id"],
            team_name=match["teamA"]["name"],
            competition=competition,
        )
        away_team, away_team_created = self._get_or_create_competition_team(
            match_id=match["id"],
            side="away",
            team_sfi_id=match["teamB"]["id"],
            team_name=match["teamB"]["name"],
            competition=competition,
        )

        teams_created = int(home_team_created) + int(away_team_created)

        if status == SFIService.SFI_NOT_STARTED_STATUS:
            return self._upsert_not_started_match(match, competition, home_team, away_team), teams_created

        return self._update_ended_match(match), teams_created

    def _get_or_create_competition_team(
        self,
        match_id: str,
        side: str,
        team_sfi_id: str,
        team_name: str,
        competition: Competition,
    ) -> tuple[Team, bool]:
        team, created = Team.objects.get_or_create(
            sfi_id=team_sfi_id,
            defaults={"name": team_name},
        )

        if not competition.teams.filter(pk=team.pk).exists():
            competition.teams.add(team)

        if created:
            msg = (
                f"  NEW TEAM: created {team_name} (sfi_id={team_sfi_id}) "
                f"for competition '{competition}' while processing match {match_id} ({side})."
            )
            self.stdout.write(msg)
            logger.info(msg)

        return team, created

    def _upsert_not_started_match(
        self,
        match: SFIMatch,
        competition: Competition,
        home_team: Team,
        away_team: Team,
    ) -> ProcessMatchResult:
        date_time = self._parse_match_datetime(match["date"])

        _, created = Match.objects.update_or_create(
            sfi_id=match["id"],
            defaults={
                "competition": competition,
                "home_team": home_team,
                "away_team": away_team,
                "date_time": date_time,
                "status": Match.NOT_STARTED,
            },
        )

        return ProcessMatchResult.created if created else ProcessMatchResult.updated

    def _update_ended_match(self, match: SFIMatch) -> ProcessMatchResult:
        match_instance = Match.objects.filter(sfi_id=match["id"]).first()
        if match_instance is None:
            logger.warning("ENDED match %s not found in DB — skipping creation.", match["id"])
            return ProcessMatchResult.skipped

        home_goals = match["teamA"]["score"]["2h"]
        away_goals = match["teamB"]["score"]["2h"]
        has_changes = (
            match_instance.status != Match.FINSHED
            or match_instance.home_goals != home_goals
            or match_instance.away_goals != away_goals
        )
        needs_consolidation = match_instance.guesses.filter(consolidated=False).exists()

        if has_changes or needs_consolidation:
            match_instance.status = Match.FINSHED
            match_instance.home_goals = home_goals
            match_instance.away_goals = away_goals
            match_instance.save(update_fields=["status", "home_goals", "away_goals"])

        return ProcessMatchResult.updated

    @staticmethod
    def _parse_match_datetime(date_str: str) -> datetime:
        return datetime.strptime(date_str, "%Y-%m-%d %H:%M:%S").replace(tzinfo=timezone.utc)
