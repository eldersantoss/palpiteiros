from time import sleep

from django.conf import settings
from django.core.management.base import BaseCommand, CommandParser

from core.models import Competition, CompetitionGroup, Team
from core.services.sfi import SFIService


class Command(BaseCommand):
    help = "Sync competition groups from Soccer Football Info API."

    def add_arguments(self, parser: CommandParser) -> None:
        parser.add_argument(
            "--sfi-ids",
            nargs="+",
            default=[],
            metavar="SFI_ID",
            help="SFI championship IDs to sync (default: all competitions with sfi_id set).",
        )
        parser.add_argument(
            "--year",
            type=int,
            default=2026,
            help="Season year to fetch (default: 2026).",
        )
        parser.add_argument(
            "--sleep-seconds",
            type=float,
            default=5,
            help="Seconds to wait between API requests (default: 5).",
        )
        parser.add_argument(
            "--sync-deletions",
            action="store_true",
            default=False,
            help="Remove groups that are no longer returned by the API.",
        )

    def handle(self, *args, **options) -> None:
        sfi_ids = options["sfi_ids"]
        year = options["year"]
        sleep_seconds = options["sleep_seconds"]
        sync_deletions = options["sync_deletions"]

        qs = Competition.objects.exclude(sfi_id__isnull=True).exclude(sfi_id="")
        if sfi_ids:
            qs = qs.filter(sfi_id__in=sfi_ids)

        if not qs.exists():
            self.stdout.write("No competitions found.")
            return

        service = SFIService(api_key=settings.SFI_API_KEY, api_host=settings.SFI_API_HOST)

        for competition in qs:
            self.stdout.write(f"Syncing groups for {competition} (sfi_id={competition.sfi_id})…")

            try:
                groups_data = service.get_groups_of_championship(competition.sfi_id, year)
            except Exception as exc:
                self.stderr.write(f"  Error fetching groups: {exc}")
                if sleep_seconds > 0:
                    sleep(sleep_seconds)
                continue

            if not groups_data:
                self.stdout.write("  No groups returned by API.")
                if sleep_seconds > 0:
                    sleep(sleep_seconds)
                continue

            api_group_names = set()
            for group_data in groups_data:
                group_name = group_data["name"]
                api_group_names.add(group_name)

                group, _ = CompetitionGroup.objects.get_or_create(
                    competition=competition,
                    name=group_name,
                )

                team_sfi_ids = [t["id"] for t in group_data["teams"] if t.get("id")]
                teams = list(Team.objects.filter(sfi_id__in=team_sfi_ids))
                group.teams.set(teams)

                self.stdout.write(f"  Group '{group_name}': {len(teams)} team(s) synced.")

            if sync_deletions:
                deleted_count, _ = CompetitionGroup.objects.filter(
                    competition=competition,
                ).exclude(name__in=api_group_names).delete()
                if deleted_count:
                    self.stdout.write(f"  Removed {deleted_count} stale group(s).")

            if sleep_seconds > 0:
                sleep(sleep_seconds)
