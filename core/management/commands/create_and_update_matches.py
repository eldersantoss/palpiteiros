from django.core.cache import cache
from django.core.management.base import BaseCommand, CommandParser

from core.models import Competition


class Command(BaseCommand):
    help = "For each registered competition, uses the Football API to create new matches and update those already registered."

    def add_arguments(self, parser: CommandParser) -> None:
        parser.add_argument(
            "--days_from",
            type=int,
            help="Number of days ago from which matches will be fetched",
        )
        parser.add_argument(
            "--days_ahead",
            type=int,
            help="Number of days ahead to which matches will be fetched",
        )

    def handle(self, *args, **options):
        days_from = options.get("days_from")
        days_ahead = options.get("days_ahead")

        competitions = Competition.objects.filter(in_progress=True)
        if not competitions.exists():
            self.stdout.write("No competitions registered yet.")
            return

        for comp in competitions:
            try:
                created, updated = comp.create_and_update_matches(days_from, days_ahead)
                self.stdout.write(f"{len(created)} matches created and {len(updated)} updated matches for {comp}...")

            except Exception as e:
                self.stderr.write(f"Error when updating {comp}: {e}")

        self.stdout.write("Cleaning cache data...")
        cache.clear()

        self.stdout.write("Competitions update done.")
