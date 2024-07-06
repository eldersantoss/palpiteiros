from django.core.cache import cache
from django.core.management.base import BaseCommand, CommandParser
from django.utils import timezone

from core.models import Competition


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
            "--days_from",
            type=int,
            help="Number of days ago from which matches will be fetched",
            default=3,
        )
        parser.add_argument(
            "--days_ahead",
            type=int,
            help="Number of days ahead to which matches will be fetched",
            default=3,
        )

    def handle(self, *args, **options):
        season = options.get("season")
        days_from = options.get("days_from")
        days_ahead = options.get("days_ahead")

        start_date = (timezone.now().replace(year=season) - timezone.timedelta(days=days_from)).date
        end_date = (timezone.now().replace(year=season) + timezone.timedelta(days=days_ahead)).date
        self.stdout.write(f"Getting matches for all in progress Competitions from {start_date} to {end_date}...")

        competitions = Competition.objects.filter(in_progress=True)
        if not competitions.exists():
            self.stdout.write("No competitions registered yet.")
            return

        for comp in competitions:
            try:
                created, updated = comp.create_and_update_matches(season, days_from, days_ahead)
                self.stdout.write(f"{len(created)} matches created and {len(updated)} updated matches for {comp}...")

            except Exception as e:
                self.stderr.write(f"Error when updating {comp}: {e}")

        self.stdout.write("Cleaning cache data...")
        cache.clear()

        self.stdout.write("Competitions update done.")
