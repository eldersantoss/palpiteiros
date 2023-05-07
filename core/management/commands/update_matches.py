from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone

from core.models import Competition


class Command(BaseCommand):
    help = "For each registered competition, send a request to the Football API to update matches."

    def handle(self, *args, **options):
        competitions = Competition.objects.all()

        if not competitions.exists():
            self.stdout.write("No competitions to get matches.")

        today = timezone.now().date()
        self.stdout.write(f"Fetching matches from today ({today})...")

        for competition in competitions:
            updated_matches = competition.update_matches()
            self.stdout.write(
                f"{len(updated_matches)} updated matches for {competition}..."
            )

        self.stdout.write("Matches update done.")
