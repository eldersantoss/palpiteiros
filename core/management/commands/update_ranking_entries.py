import pytz
from django.conf import settings
from django.core.management.base import BaseCommand
from django.db import transaction

from core.models import Guess, RankingEntry


class Command(BaseCommand):
    help = "Deletes all existing ranking entries and recalculates them from scratch based on consolidated guesses."

    @transaction.atomic
    def handle(self, *args, **options):
        self.stdout.write("Starting full recalculation of RankingEntry table...")

        self.stdout.write("Deleting existing ranking entries...")
        deleted_count, _ = RankingEntry.objects.all().delete()
        self.stdout.write(
            self.style.SUCCESS(f"Successfully deleted {deleted_count} old entries.")
        )

        self.stdout.write("Aggregating scores from consolidated guesses...")
        ranking_data = {}
        guesses = Guess.objects.filter(consolidated=True).prefetch_related(
            "pools", "guesser", "match"
        )
        total_guesses = guesses.count()
        processed_guesses = 0

        for guess in guesses:
            if not guess.guesser:
                continue  # Pula palpites órfãos, se houver

            match_date = guess.match.date_time.astimezone(
                pytz.timezone(settings.TIME_ZONE)
            )
            year = match_date.year
            month = match_date.month
            week = match_date.isocalendar().week

            periods = [
                (0, 0, 0),  # General
                (year, 0, 0),  # Annual
                (year, month, 0),  # Monthly
                (year, 0, week),  # Weekly
            ]

            for pool in guess.pools.all():
                for period in periods:
                    key = (pool.id, guess.guesser.id, period[0], period[1], period[2])
                    ranking_data.setdefault(key, 0)
                    ranking_data[key] += guess.score

            processed_guesses += 1
            if processed_guesses % 1000 == 0:
                self.stdout.write(
                    f"{processed_guesses}/{total_guesses} guesses processed..."
                )

        self.stdout.write(
            f"Aggregation complete. {len(ranking_data)} ranking entries to be created."
        )

        self.stdout.write("Creating new ranking entries in bulk...")
        entries_to_create = [
            RankingEntry(
                pool_id=pool_id,
                guesser_id=guesser_id,
                year=year,
                month=month,
                week=week,
                score=score,
            )
            for (pool_id, guesser_id, year, month, week), score in ranking_data.items()
        ]

        RankingEntry.objects.bulk_create(entries_to_create, batch_size=1000)

        self.stdout.write(
            self.style.SUCCESS("RankingEntry table has been successfully rebuilt.")
        )
