from time import sleep

from django.conf import settings
from django.core.management.base import BaseCommand, CommandParser

from core.models import Competition
from core.services.sfi import SFIService


class Command(BaseCommand):
    help = "Sync competitions from Soccer Football Info API by SFI championship ID."

    def add_arguments(self, parser: CommandParser) -> None:
        parser.add_argument(
            "sfi_ids",
            nargs="+",
            metavar="SFI_ID",
            help="SFI championship IDs to sync, separated by spaces.",
        )
        parser.add_argument(
            "--sleep-seconds",
            type=float,
            default=5,
            help="Seconds to wait between API requests (default: 5).",
        )

    def handle(self, *args, **options) -> None:
        sfi_ids = options["sfi_ids"]
        sleep_seconds = options["sleep_seconds"]

        service = SFIService(api_key=settings.SFI_API_KEY, api_host=settings.SFI_API_HOST)

        for sfi_id in sfi_ids:
            try:
                championship = service.get_championship(sfi_id)
            except Exception as exc:
                self.stderr.write(f"Error fetching championship {sfi_id}: {exc}")
                if sleep_seconds > 0:
                    sleep(sleep_seconds)
                continue

            if championship is None:
                self.stderr.write(f"Championship {sfi_id} not found.")
                if sleep_seconds > 0:
                    sleep(sleep_seconds)
                continue

            competition, created = Competition.objects.update_or_create(
                sfi_id=sfi_id,
                defaults={"name": championship["name"]},
            )

            action = "created" if created else "updated"
            self.stdout.write(f"Competition '{competition.name}' (sfi_id={sfi_id}) was {action}.")

            if sleep_seconds > 0:
                sleep(sleep_seconds)
