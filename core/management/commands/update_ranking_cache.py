from django.conf import settings
from django.core.cache import cache
from django.core.management.base import BaseCommand, CommandParser
from django.utils import timezone

from core.models import GuessPool


# TODO: adicionar opção de data inicial para as partidas que serão consolidadas
class Command(BaseCommand):
    help = "Consolidates ranking data for all pools and saves it in cache."

    def add_arguments(self, parser: CommandParser) -> None:
        parser.add_argument(
            "guess_pool_ids",
            type=int,
            nargs="+",
            help="Guess Pool ids separeted by space",
        )

    def handle(self, *args, **options):
        self.stdout.write("Starting ranking data consolidation")

        current_date = timezone.datetime.today()
        current_year = current_date.year
        current_week = current_date.isocalendar().week
        guess_pool_ids = options["guess_pool_ids"]

        pools = GuessPool.objects.filter(id__in=guess_pool_ids) if len(guess_pool_ids) else GuessPool.objects.all()

        for pool in pools:
            self.stdout.write(f"Consolidating {pool.name} pool")

            # General ranking (year = 0)
            self.stdout.write("Processing general ranking")
            cache_key = settings.RANKING_CACHE_PREFIX + f"_{pool.uuid}_{str(0)}{str(0)}{str(0)}"
            guessers_data = pool.get_guessers_with_score_and_guesses(
                year=0,
                month=0,
                week=0,
            )
            cache.set(cache_key, guessers_data, None)

            # Annual ranking (month = 0)
            self.stdout.write("Processing annual ranking")
            cache_key = settings.RANKING_CACHE_PREFIX + f"_{pool.uuid}_{str(current_year)}{str(0)}{str(0)}"
            guessers_data = pool.get_guessers_with_score_and_guesses(
                year=current_year,
                month=0,
                week=0,
            )

            # Monthly ranking (week = 0)
            self.stdout.write("Processing monthly ranking")
            cache.set(cache_key, guessers_data, None)
            for month in range(1, 13):
                cache_key = settings.RANKING_CACHE_PREFIX + f"_{pool.uuid}_{str(current_year)}{str(month)}{str(0)}"
                guessers_data = pool.get_guessers_with_score_and_guesses(
                    year=current_year,
                    month=month,
                    week=0,
                )
                cache.set(cache_key, guessers_data, None)

            # Weekly ranking
            self.stdout.write("Processing weekly ranking")
            for month in range(1, 13):
                for week in range(1, current_week + 1):
                    cache_key = (
                        settings.RANKING_CACHE_PREFIX + f"_{pool.uuid}_{str(current_year)}{str(month)}{str(week)}"
                    )
                    guessers_data = pool.get_guessers_with_score_and_guesses(
                        year=current_year,
                        month=month,
                        week=week,
                    )
                    cache.set(cache_key, guessers_data, None)

        self.stdout.write("Ranking data consolidation finished")
