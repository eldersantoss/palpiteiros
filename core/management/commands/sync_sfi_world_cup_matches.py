"""Management command: sync_sfi_world_cup_matches.

Fetches matches from the Soccer Football Info (SFI) API for the World Cup competition
and upserts them into the database.
"""

import logging
from datetime import datetime, timezone
from enum import StrEnum
from math import ceil
from time import sleep

from django.conf import settings
from django.core.management.base import BaseCommand
from django.utils import timezone as django_timezone

from core.models import Competition, Match, Team
from core.services.sfi import SFIMatch, SFIService

logger = logging.getLogger(__name__)


class ProcessMatchResult(StrEnum):
    created = "created"
    updated = "updated"
    skipped = "skipped"


class Command(BaseCommand):
    """Create and update matches for the World Cup using the Soccer Football Info API."""

    help = (
        "Fetches World Cup matches from the Soccer Football Info API and creates or "
        "updates them in the database."
    )

    WORLD_CUP_SFI_ID = "5085a3cde16c822b"

    def handle(self, *args, **options) -> None:
        """Entry point; orchestrates match processing for World Cup."""
        competition = Competition.objects.filter(sfi_id=self.WORLD_CUP_SFI_ID).first()

        if not competition:
            self.stdout.write(f"Competition with SFI ID {self.WORLD_CUP_SFI_ID} not registered or in progress. Aborting.")
            return

        competitions_by_sfi_id = {self.WORLD_CUP_SFI_ID: competition}

        self.stdout.write(f"sync_sfi_world_cup_matches: processing World Cup matches (ID: {self.WORLD_CUP_SFI_ID})")

        service = SFIService(api_key=settings.SFI_API_KEY, api_host=settings.SFI_API_HOST)

        try:
            matches = self._fetch_all_matches_for_championship(service, self.WORLD_CUP_SFI_ID)
        except Exception:
            logger.exception("Failed to fetch SFI matches for World Cup.")
            self.stderr.write("  ERROR: could not fetch matches, aborting.")
            return

        created, updated, skipped, teams_created = 0, 0, 0, 0
        updated_comp_ids = set()

        for match in matches:
            outcome, created_teams_for_match = self._process_match(match, competitions_by_sfi_id)
            teams_created += created_teams_for_match

            if outcome == ProcessMatchResult.created:
                created += 1
                updated_comp_ids.add(competition.id)
            elif outcome == ProcessMatchResult.updated:
                updated += 1
                updated_comp_ids.add(competition.id)
            else:
                skipped += 1

        self.stdout.write(
            f"  Result: {created} created, {updated} updated, {skipped} skipped, "
            f"{teams_created} teams registered."
        )

        if updated_comp_ids:
            self.stdout.write(f"Recalculating standings for updated competitions: {updated_comp_ids}")
            from core.models import CompetitionGroup
            for group in CompetitionGroup.objects.filter(competition_id__in=updated_comp_ids):
                self.stdout.write(f"  Recalculating standings for group {group}...")
                group.recalculate_standings()

        self.stdout.write("sync_sfi_world_cup_matches finished.")

    def _fetch_all_matches_for_championship(self, service: SFIService, championship_id: str) -> list[SFIMatch]:
        """Return every SFI match for the given championship, handling pagination transparently.

        The response is paginated at 25 items per page, so we iterate until all
        pages are consumed.

        A short sleep between paginated requests respects the API rate limit
        defined by ``settings.SFI_API_REQUESTS_INTERVAL``.
        """
        self.stdout.write(f"    → GET matches for competition {championship_id} (page 1)")
        first_page = service.get_matches_by_championship(championship_id, page=1)
        matches: list[SFIMatch] = list(first_page.get("result", []))

        pagination = first_page.get("pagination", [])
        if not pagination:
            # Unexpected: treat as a single page.
            return matches

        total_items: int = pagination[0]["items"]
        per_page: int = pagination[0]["per_page"]
        total_pages: int = ceil(total_items / per_page)

        for page in range(2, total_pages + 1):
            sleep(settings.SFI_API_REQUESTS_INTERVAL)
            self.stdout.write(f"    → GET matches for competition {championship_id} (page {page}/{total_pages})")
            response = service.get_matches_by_championship(championship_id, page=page)
            matches.extend(response.get("result", []))

        return matches

    def _process_match(
        self,
        match: SFIMatch,
        competitions_by_sfi_id: dict[str, Competition],
    ) -> tuple[ProcessMatchResult, int]:
        """Process a single SFI match dict and apply the appropriate DB operation.

        Returns a tuple ``(result, teams_created)`` where ``result`` is one of
        ``"created"``, ``"updated"``, or ``"skipped"``.
        """
        competition = competitions_by_sfi_id.get(match["championship"]["id"])
        if competition is None:
            # Not a tracked competition — silently ignore.
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
        """Return a team by SFI ID, creating and linking it to the competition when needed."""
        team, created = Team.objects.get_or_create(
            sfi_id=team_sfi_id,
            defaults={"name": team_name},
        )

        if not competition.teams.filter(pk=team.pk).exists():
            competition.teams.add(team)

        if created:
            msg = (
                f"    NEW TEAM: created {team_name} (sfi_id={team_sfi_id}) "
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
        """Create or update a NOT_STARTED match without touching goal fields."""
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
        """Update the goals of a ENDED match that already exists in the database.

        If the match is not yet registered (e.g. it happened before this command
        was set up), it is skipped rather than created with incomplete data.
        """
        match_instance = Match.objects.filter(sfi_id=match["id"]).first()
        if match_instance is None:
            logger.warning(
                "ENDED match %s not found in DB — skipping creation.",
                match["id"],
            )
            return ProcessMatchResult.skipped

        home_goals = match["teamA"]["score"]["2h"]
        away_goals = match["teamB"]["score"]["2h"]
        date_time = self._parse_match_datetime(match["date"])

        home_fouls = match["teamA"]["stats"]["fouls"]
        away_fouls = match["teamB"]["stats"]["fouls"]
        _hyc, _ayc = home_fouls["y_c"], away_fouls["y_c"]
        _hrc, _arc = home_fouls["r_c"], away_fouls["r_c"]
        home_yellow_cards = int(_hyc) if _hyc is not None else None
        away_yellow_cards = int(_ayc) if _ayc is not None else None
        home_red_cards = int(_hrc) if _hrc is not None else None
        away_red_cards = int(_arc) if _arc is not None else None

        has_changes = (
            match_instance.status != Match.FINSHED
            or match_instance.home_goals != home_goals
            or match_instance.away_goals != away_goals
            or match_instance.date_time != date_time
            or match_instance.home_yellow_cards != home_yellow_cards
            or match_instance.away_yellow_cards != away_yellow_cards
            or match_instance.home_red_cards != home_red_cards
            or match_instance.away_red_cards != away_red_cards
        )
        needs_consolidation = match_instance.guesses.filter(consolidated=False).exists()

        if has_changes or needs_consolidation:
            match_instance.status = Match.FINSHED  # "FT"
            match_instance.home_goals = home_goals
            match_instance.away_goals = away_goals
            match_instance.date_time = date_time
            match_instance.home_yellow_cards = home_yellow_cards
            match_instance.away_yellow_cards = away_yellow_cards
            match_instance.home_red_cards = home_red_cards
            match_instance.away_red_cards = away_red_cards
            match_instance.save(
                update_fields=[
                    "status",
                    "home_goals",
                    "away_goals",
                    "date_time",
                    "home_yellow_cards",
                    "away_yellow_cards",
                    "home_red_cards",
                    "away_red_cards",
                ]
            )

        return ProcessMatchResult.updated

    @staticmethod
    def _parse_match_datetime(date_str: str) -> datetime:
        """Parse the SFI date string (``"YYYY-MM-DD HH:MM:SS"``) as a UTC datetime."""
        return datetime.strptime(date_str, "%Y-%m-%d %H:%M:%S").replace(tzinfo=timezone.utc)
