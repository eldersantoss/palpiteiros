from django.core.management.base import BaseCommand, CommandParser

from core.models import Competition


class Command(BaseCommand):
    help = "Get data from Football API and create Competition model instances."

    def add_arguments(self, parser: CommandParser) -> None:
        parser.add_argument(
            "season",
            type=int,
            help="Football API league season",
        )
        parser.add_argument(
            "league_ids",
            type=int,
            nargs="+",
            help="Football API league ids separeted by space",
        )

    def handle(self, *args, **options):
        season = options["season"]
        league_ids = options["league_ids"]

        for league_id in league_ids:
            Competition.create_or_update(season, league_id)

        self.stdout.write(
            "Registration of competitions was done. Now, you need register teams for competitions with create_or_update_teams_for_competitions command."
        )
