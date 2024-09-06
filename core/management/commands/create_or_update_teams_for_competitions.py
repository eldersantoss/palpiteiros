from time import sleep

from django.conf import settings
from django.core.management.base import BaseCommand, CommandParser

from core.models import Competition, Team
from core.services.football import FootballApiService


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

        if not competitions.exists():
            self.stdout.write(
                f"No competitions has been found with provided ids: {', '.join(str(i) for i in league_ids)}."
            )

        for competition in competitions:
            teams_data = FootballApiService.get_teams_of_league_by_season(competition.data_source_id, season)
            sleep(settings.FOOTBALL_API_REQUESTS_INTERVAL)

            if teams_data:
                teams = []
                for data in teams_data:
                    data_source_id = data["team"]["id"]
                    name = data["team"]["name"]
                    code = data["team"]["code"]

                    team, _ = Team.objects.get_or_create(
                        data_source_id=data_source_id,
                        name=name,
                        code=code,
                    )
                    teams.append(team)

                competition.teams.set(teams)

                self.stdout.write(f"Teams updated for {competition.name}")

            else:
                self.stdout.write(
                    f"No teams has been found for competition {competition.data_source_id} in the {season} season"
                )
