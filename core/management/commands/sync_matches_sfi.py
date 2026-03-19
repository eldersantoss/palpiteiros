"""Management command: sync_matches_sfi.

Fetches matches from the Soccer Football Info (SFI) API for a configurable
date range and upserts them into the database.

Default window: yesterday through the two days after today (4 dates total).
Matches from competitions not registered with an SFI ID are silently skipped.
Teams not found for a tracked competition are created and linked automatically.
"""

import logging
from datetime import date, datetime, timedelta, timezone
from enum import StrEnum
from math import ceil
from time import sleep

from django.conf import settings
from django.core.management.base import BaseCommand, CommandParser
from django.utils import timezone as django_timezone

from core.models import Competition, Match, Team
from core.services.sfi import SFIMatch, SFIService

logger = logging.getLogger(__name__)


class ProcessMatchResult(StrEnum):
    created = "created"
    updated = "updated"
    skipped = "skipped"


class Command(BaseCommand):
    """Create and update matches using the Soccer Football Info API."""

    help = (
        "Fetches matches from the Soccer Football Info API and creates or updates "
        "them in the database for the given date range."
    )

    def add_arguments(self, parser: CommandParser) -> None:
        """Register optional CLI arguments for date filtering."""
        parser.add_argument(
            "--date",
            type=date.fromisoformat,
            help="Process a single date only (YYYY-MM-DD). Overrides --start_date / --end_date.",
            default=None,
        )
        parser.add_argument(
            "--start_date",
            type=date.fromisoformat,
            help="Start of the date range to process (YYYY-MM-DD). Defaults to yesterday.",
            default=None,
        )
        parser.add_argument(
            "--end_date",
            type=date.fromisoformat,
            help="End of the date range to process (YYYY-MM-DD). Defaults to 2 days from now.",
            default=None,
        )

    def handle(self, *args, **options) -> None:
        """Entry point; orchestrates date iteration and match processing."""
        # Load competitions first so we can exit early if none are registered,
        # avoiding unnecessary date computation and API calls.
        competitions_by_sfi_id = {
            comp.sfi_id: comp for comp in Competition.objects.filter(sfi_id__isnull=False) if comp.sfi_id is not None
        }

        if not competitions_by_sfi_id:
            self.stdout.write("No competitions with an SFI ID are registered. Aborting.")
            return

        today = django_timezone.now().date()
        dates = self._build_date_list(options, today)

        self.stdout.write(f"sync_matches_sfi: processing {len(dates)} date(s): {dates[0]} → {dates[-1]}")

        service = SFIService(api_key=settings.SFI_API_KEY, api_host=settings.SFI_API_HOST)

        for target_date in dates:
            self._process_date(service, target_date, competitions_by_sfi_id, today)

        self.stdout.write("sync_matches_sfi finished.")

    def _build_date_list(self, options: dict, today: date) -> list[date]:
        """Return the ordered list of dates to process based on CLI options.

        - ``--date`` overrides everything and returns a single-element list.
        - ``--start_date`` / ``--end_date`` define an inclusive range.
        - Default: [yesterday, today, today+1, today+2].
        """
        single = options.get("date")
        if single:
            return [single]

        start = options.get("start_date") or (today - timedelta(days=1))
        end = options.get("end_date") or (today + timedelta(days=1))

        return [start + timedelta(days=i) for i in range((end - start).days + 1)]

    def _process_date(
        self,
        service: SFIService,
        target_date: date,
        competitions_by_sfi_id: dict[str, Competition],
        today: date,
    ) -> None:
        """Fetch and process all SFI matches for a single calendar day."""
        self.stdout.write(f"  Fetching matches for {target_date}...")

        try:
            matches = self._fetch_all_matches_for_date(service, target_date, today)
        except Exception:
            logger.exception("Failed to fetch SFI matches for %s.", target_date)
            self.stderr.write(f"  ERROR: could not fetch matches for {target_date}, skipping.")
            return

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
            f"  {target_date}: {created} created, {updated} updated, {skipped} skipped, "
            f"{teams_created} teams registered."
        )

    def _fetch_all_matches_for_date(self, service: SFIService, target_date: date, today: date) -> list[SFIMatch]:
        """Return every SFI match for *target_date*, handling pagination transparently.

        For past dates the API responds with all results on a single page
        (``pagination`` is an empty list).  For present and future dates the
        response is paginated at 25 items per page, so we iterate until all
        pages are consumed.

        A short sleep between paginated requests respects the API rate limit
        defined by ``settings.SFI_API_REQUESTS_INTERVAL``.
        """
        is_past = target_date < today

        if is_past:
            # Single-page response — pagination field will be [].
            self.stdout.write(f"    → GET matches {target_date} (page 1, past date)")
            response = service.get_matches_by_day(target_date, page=1)
            return response.get("result", [])

        # Present or future: paginated response.
        self.stdout.write(f"    → GET matches {target_date} (page 1)")
        first_page = service.get_matches_by_day(target_date, page=1)
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
            self.stdout.write(f"    → GET matches {target_date} (page {page}/{total_pages})")
            response = service.get_matches_by_day(target_date, page=page)
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
        updated_count = Match.objects.filter(sfi_id=match["id"]).update(
            status=Match.FINSHED,  # "FT"
            home_goals=match["teamA"]["score"]["o"] or match["teamA"]["score"]["f"],
            away_goals=match["teamB"]["score"]["o"] or match["teamB"]["score"]["f"],
        )

        if updated_count == 0:
            logger.warning(
                "ENDED match %s not found in DB — skipping creation.",
                match["id"],
            )
            return ProcessMatchResult.skipped

        return ProcessMatchResult.updated

    @staticmethod
    def _parse_match_datetime(date_str: str) -> datetime:
        """Parse the SFI date string (``"YYYY-MM-DD HH:MM:SS"``) as a UTC datetime."""
        return datetime.strptime(date_str, "%Y-%m-%d %H:%M:%S").replace(tzinfo=timezone.utc)
