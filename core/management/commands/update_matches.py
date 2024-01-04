from django.core.management.base import BaseCommand, CommandParser
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
        days_from = options.get("days_from")
        days_ahead = options.get("days_ahead")
        today = timezone.now().date()
        from_ = today - timezone.timedelta(days=days_from or 1)
        to = today + timezone.timedelta(days=days_ahead or 0)

        self.stdout.write(
            f"Fetching competitions with matches between {from_} and {to}..."
        )
        competitions = Competition.get_with_matches_on_period(from_, to)
        if not competitions.exists():
            self.stdout.write(f"No competitions with matches between {from_} and {to}.")

        for competition in competitions:
            updated_matches = competition.update_matches(days_from, days_ahead)
            self.stdout.write(
                f"{len(updated_matches)} updated matches for {competition}..."
            )

        self.stdout.write("Matches update done.")
