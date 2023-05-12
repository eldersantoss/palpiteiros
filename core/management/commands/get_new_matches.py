from django.core.management.base import BaseCommand, CommandError, CommandParser
from django.utils import timezone

from core.models import Competition


class Command(BaseCommand):
    help = "For each registered competition, send a request to the Football API to get new matches."

    def add_arguments(self, parser: CommandParser) -> None:
        parser.add_argument(
            "days_ahead",
            type=int,
            help="Days ahead limit to fetch matches",
        )

    def handle(self, *args, **options):
        competitions = Competition.objects.all()
        days_ahead = options["days_ahead"]

        if not competitions.exists():
            self.stdout.write("No competitions to get matches.")

        today = timezone.now().date()
        deadline = (timezone.now() + timezone.timedelta(days=days_ahead)).date()
        self.stdout.write(f"Fetching matches from {today} (today) to {deadline}...")

        for competition in competitions:
            new_matches = competition.get_new_matches(days_ahead)
            self.stdout.write(
                f"{len(new_matches)} new matches registered for {competition}..."
            )

        self.stdout.write("Registration of new matches done.")
