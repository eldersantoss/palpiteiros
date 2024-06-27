from django.core.management.base import BaseCommand, CommandParser

from core.models import Competition


class Command(BaseCommand):
    help = "Get data from Football API and update teams for the competitions."

    def add_arguments(self, parser: CommandParser) -> None:
        parser.add_argument("--season", type=int, help="Football API league season", default=None)
        parser.add_argument(
            "--league_ids", type=int, nargs="+", help="Football API league ids separeted by space", default=[]
        )

    def handle(self, *args, **options):
        season = options["season"]
        league_ids = options["league_ids"]

        data_source_ids = [league_id + season for league_id in league_ids]

        competitions = (
            Competition.objects.filter(data_source_id__in=data_source_ids)
            if data_source_ids
            else Competition.objects.all()
        )

        for competition in competitions:
            competition.get_teams()
            self.stdout.write(f"Teams updated for {competition.name}")

        self.stdout.write("Teams of competitions updating done.")
