from time import sleep

import requests
from django.conf import settings
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

        api_url = f"https://{settings.FOOTBALL_API_HOST}/leagues"
        headers = {
            "x-rapidapi-key": settings.FOOTBALL_API_KEY,
            "x-rapidapi-host": settings.FOOTBALL_API_HOST,
        }

        competitions: list[Competition] = []
        for league_id in league_ids:
            params = {"id": league_id}

            # TODO: tratar possíveis exceções
            response = requests.get(api_url, headers=headers, params=params)
            sleep(settings.FOOTBALL_API_RATE_LIMIT_TIME)

            json_data = response.json()
            json_data_response = json_data["response"][0]

            seasons = [d["year"] for d in json_data_response["seasons"]]
            if season not in seasons:
                self.stderr.write(f"Season {season} not found for league {league_id}.")
                continue

            competition, created = Competition.objects.get_or_create(
                data_source_id=json_data_response["league"]["id"],
                name=json_data_response["league"]["name"],
                season=season,
            )
            if created:
                competitions.append(competition)

        self.stdout.write(f"{len(competitions)} competitions created.")

        for competition in competitions:
            created_teams = competition.get_teams()
            self.stdout.write(
                f"{len(created_teams)} teams registered on competition {competition}."
            )

            pool = competition.create_public_pool()
            if pool is not None:
                self.stdout.write(f"{pool} pool was created.")

        self.stdout.write("Registration of competitions done.")
