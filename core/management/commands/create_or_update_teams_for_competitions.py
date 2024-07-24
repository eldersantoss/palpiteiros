from django.core.management.base import BaseCommand, CommandParser

from core.models import Competition


class Command(BaseCommand):
    help = "Get data from Football API and update teams for the competitions."

    def add_arguments(self, parser: CommandParser) -> None:
        parser.add_argument(
            "season",
            type=int,
            nargs=1,
            help="Season of the league whose teams will be created or updated",
        )
        parser.add_argument(
            "league_ids",
            type=int,
            nargs="+",
            help="Football API league ids separeted by space",
            default=[],
        )

    def handle(self, *args, **options):
        season = options["season"]
        league_ids = options["league_ids"]

        competitions = (
            Competition.objects.filter(data_source_id__in=league_ids) if league_ids else Competition.objects.all()
        )

        for competition in competitions:
            competition.get_teams(season)
            self.stdout.write(f"Teams updated for {competition.name}")

        self.stdout.write("Update of teams in competitions done.")
