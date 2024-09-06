from datetime import date
from time import sleep

from django.conf import settings
from django.core.cache import cache
from django.core.management.base import BaseCommand, CommandParser
from django.utils import timezone

from core.models import Competition
from core.services.football import FootballApiService


class Command(BaseCommand):
    help = "For each registered competition, uses the Football API to create new matches and update those already registered."

    def add_arguments(self, parser: CommandParser) -> None:
        parser.add_argument(
            "--season",
            type=int,
            help="Season of the league whose teams will be created or updated",
            default=timezone.now().year,
        )
        parser.add_argument(
            "--start_date",
            type=date.fromisoformat,
            help="Start date for searching matches (YYYY-MM-DD)",
            default=(timezone.now() - timezone.timedelta(days=3)).date(),
        )
        parser.add_argument(
            "--end_date",
            type=date.fromisoformat,
            help="End date for searching matches (YYYY-MM-DD)",
            default=(timezone.now() + timezone.timedelta(days=3)).date(),
        )

    def handle(self, *args, **options):
        season = options.get("season")
        start_date = options.get("start_date")
        end_date = options.get("end_date")

        self.stdout.write(f"Getting matches for all in progress Competitions from {start_date} to {end_date}")

        competitions = Competition.objects.filter(in_progress=True)
        if not competitions.exists():
            self.stdout.write("There are no registered competitions in progress")
            return

        for comp in competitions:
            try:
                created, updated = FootballApiService.create_and_update_matches(comp, season, start_date, end_date)
                sleep(settings.FOOTBALL_API_REQUESTS_INTERVAL)
                self.stdout.write(f"{len(created)} matches created and {len(updated)} updated matches for {comp}")

            except Exception as e:
                self.stderr.write(f"Error when updating {comp}: {e}")

        try:
            self.stdout.write("Cleaning cache data")
            cache.clear()

        except:
            self.stderr.write("Error when cleaning cache data")

        self.stdout.write("Competitions update done")
