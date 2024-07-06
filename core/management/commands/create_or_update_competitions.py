import logging

from django.core.management.base import BaseCommand, CommandParser

from core.models import Competition
from core.services.football import FootballApiService

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = "Get data from Football API and create Competition model instances."

    def add_arguments(self, parser: CommandParser) -> None:
        parser.add_argument(
            "league_ids",
            type=int,
            nargs="+",
            help="Football API league ids separeted by space",
        )

    def handle(self, *args, **options):
        league_ids = options["league_ids"]

        for league_id in league_ids:
            league_data = FootballApiService.get_league_by_id(league_id)

            if not league_data:
                logger.warning(f"League {league_id} not found")
                continue

            data_source_id = league_data["league"]["id"]
            name = league_data["league"]["name"]
            competition, created = Competition.objects.update_or_create(
                data_source_id=data_source_id,
                defaults={"name": name},
            )

            action_performed = "created" if created else "updated"
            logger.info(f"Competition {competition.name} (id {competition.data_source_id}) was {action_performed}.")

        self.stdout.write(
            "Registration of competitions was done. Now, you need register teams for competitions with create_or_update_teams_for_competitions command."
        )
