from django.core.management.base import BaseCommand, CommandError, CommandParser
from django.utils import timezone

from core.models import Competition


class Command(BaseCommand):
    help = "For each registered competition, send a request to the Football API to update matches."

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
        competitions = Competition.objects.all()
        days_from = options.get("days_from")
        days_ahead = options.get("days_ahead")

        if not competitions.exists():
            self.stdout.write("No competitions to get matches.")

        today = timezone.now().date()
        from_ = today - timezone.timedelta(days=days_from or 1)
        to = today + timezone.timedelta(days=days_ahead or 0)
        self.stdout.write(f"Fetching matches from {from_} to {to}...")

        for competition in competitions:
            updated_matches = competition.update_matches(days_from, days_ahead)
            self.stdout.write(
                f"{len(updated_matches)} updated matches for {competition}..."
            )

        self.stdout.write("Matches update done.")
