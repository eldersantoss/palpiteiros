from datetime import date
from time import sleep

from django.conf import settings
from django.core import management
from django.core.cache import cache
from django.core.management.base import BaseCommand, CommandParser
from django.utils import timezone

from core.management.commands import create_or_update_teams_for_competitions
from core.models import Competition, Match, Team
from core.services.football import FootballApi


class Command(BaseCommand):
    help = "For each registered competition, uses the Football API to create new matches and update those already registered."

    def add_arguments(self, parser: CommandParser) -> None:
        parser.add_argument(
            "--start_date",
            type=date.fromisoformat,
            help="Start date for searching matches (YYYY-MM-DD)",
            default=(timezone.now() - timezone.timedelta(days=3)).date(),
        )
        parser.add_argument(
            "--end_date",
            type=date.fromisoformat,
            help="End date for searching matches (YYYY-MM-DD)",
            default=(timezone.now() + timezone.timedelta(days=3)).date(),
        )

    def handle(self, *args, **options):
        start_date = options.get("start_date")
        end_date = options.get("end_date")

        self.stdout.write(f"Getting matches for all in progress Competitions from {start_date} to {end_date}")

        competitions = Competition.objects.filter(in_progress=True)
        if not competitions.exists():
            self.stdout.write("There are no registered competitions in progress")
            return

        for comp in competitions:
            created, updated = [], []

            try:
                matches = FootballApi.get_matches_of_league_by_season_and_date_period(
                    comp.data_source_id, comp.current_season, start_date, end_date
                )
                sleep(settings.FOOTBALL_API_REQUESTS_INTERVAL)

                for match in matches:
                    home_team = Team.objects.filter(data_source_id=match["teams"]["home"]["id"]).first()
                    away_team = Team.objects.filter(data_source_id=match["teams"]["away"]["id"]).first()
                    if home_team is None or away_team is None:
                        self.stdout.write(
                            f"Unregistered teams for match {match['fixture']['id']} in {comp}, "
                            "Updating teams for this competition"
                        )
                        management.call_command(
                            create_or_update_teams_for_competitions.Command(),
                            comp.current_season,
                            comp.data_source_id,
                        )

                        home_team = Team.objects.filter(data_source_id=match["teams"]["home"]["id"]).first()
                        away_team = Team.objects.filter(data_source_id=match["teams"]["away"]["id"]).first()
                        if home_team is None or away_team is None:
                            self.stderr.write(
                                f"Teams not found for match {match['fixture']['id']} in {comp}, "
                                "skipping match creation"
                            )
                            continue

                    match_data = parse_match_data(match)
                    match_data["competition"] = comp
                    match_data["home_team"] = home_team
                    match_data["away_team"] = away_team

                    match_instance, created_instance = Match.objects.update_or_create(
                        data_source_id=match_data["data_source_id"],
                        defaults=match_data,
                    )

                    if created_instance:
                        created.append(match_instance)

                    else:
                        updated.append(match_instance)

                self.stdout.write(f"{len(created)} matches created and {len(updated)} updated matches for {comp}")

            except Exception as e:
                self.stderr.write(f"Error when updating {comp}: {e}")

        try:
            self.stdout.write("Cleaning cache data")
            cache.clear()

        except:
            self.stderr.write("Error when cleaning cache data")

        self.stdout.write("Competitions update done")


# TODO: mover para arquivo utils do service
def parse_match_data(match_raw_data: dict) -> dict:
    return {
        "data_source_id": match_raw_data["fixture"]["id"],
        "date_time": timezone.datetime.fromisoformat(match_raw_data["fixture"]["date"]),
        "status": match_raw_data["fixture"]["status"]["short"],
        "home_goals": match_raw_data["goals"]["home"],
        "away_goals": match_raw_data["goals"]["away"],
    }
