"""Management command: get_teams_of_championships_sfi.

Fetches teams for championships listed in a JSON input file using the
Soccer Football Info (SFI) API and writes a merged JSON output file.

The command keeps the same merge semantics as the original standalone script:
if a championship ID is already present in the output, its entry is replaced;
otherwise a new entry is appended.
"""

import json
import logging
from pathlib import Path
from time import sleep

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError, CommandParser

from core.services.sfi import SFIChampionshipTeamsResponse, SFIService

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    """Fetch teams for championships and persist them to a JSON file."""

    help = (
        "Fetches championship teams from the Soccer Football Info API and saves "
        "them as JSON, merging by championship ID."
    )

    def add_arguments(self, parser: CommandParser) -> None:
        """Register CLI arguments for input/output files and behavior tuning."""
        parser.add_argument(
            "--input-file",
            default="core/fixtures/soccer_football_info/main_championships.json",
            help="Path to input JSON with championships (default: core/fixtures/soccer_football_info/main_championships.json).",
        )
        parser.add_argument(
            "--output-file",
            default="core/fixtures/soccer_football_info/championships_with_teams.json",
            help=(
                "Path to output JSON file (default: "
                "core/fixtures/soccer_football_info/championships_with_teams.json)."
            ),
        )
        parser.add_argument(
            "--year",
            type=int,
            default=2026,
            help="Season year to fetch (default: 2026).",
        )
        parser.add_argument(
            "--sleep-seconds",
            type=float,
            default=5,
            help="Seconds to wait between championship requests (default: 5).",
        )

    def handle(self, *args, **options) -> None:
        """Entry point that orchestrates read, fetch, merge, and write operations."""
        input_path = Path(options["input_file"])
        output_path = Path(options["output_file"])
        year = options["year"]
        sleep_seconds = options["sleep_seconds"]

        championships = self._load_input_file(input_path)
        output = self._load_output_file(output_path)
        output_index = {entry["id"]: i for i, entry in enumerate(output) if "id" in entry}

        service = SFIService(api_key=settings.SFI_API_KEY, api_host=settings.SFI_API_HOST)

        processed = 0
        appended = 0
        replaced = 0
        failed = 0

        self.stdout.write(
            f"get_teams_of_championships_sfi: processing {len(championships)} championship(s) " f"for season {year}."
        )

        for championship in championships:
            champ_id = championship.get("id")
            champ_name = championship.get("name", "")

            if not champ_id:
                logger.warning("Skipping championship without 'id': %s", championship)
                failed += 1
                continue

            try:
                logger.info("Buscando times do championship %r (%s)", champ_name, champ_id)

                response = service.get_teams_of_championship(championship_id=champ_id, year=year)
                teams = self._extract_teams(response, year)

                if not teams:
                    logger.warning(
                        "Nenhum time encontrado para a temporada %s em %r",
                        year,
                        champ_name,
                    )

                entry = {
                    "id": champ_id,
                    "name": champ_name,
                    "teams": teams,
                }

                if champ_id in output_index:
                    output[output_index[champ_id]] = entry
                    replaced += 1
                    logger.info("Sobrescrevendo entrada existente para %r", champ_name)
                else:
                    output_index[champ_id] = len(output)
                    output.append(entry)
                    appended += 1

                processed += 1

            except Exception as exc:  # noqa: BLE001 - keep script parity: log and continue.
                failed += 1
                logger.warning("Erro ao processar championship %r: %s", champ_name, exc)
            finally:
                if sleep_seconds > 0:
                    sleep(sleep_seconds)

        self._save_output_file(output_path, output)

        self.stdout.write(
            f"Concluido: {processed} processado(s), {appended} adicionado(s), "
            f"{replaced} sobrescrito(s), {failed} falha(s)."
        )
        self.stdout.write(f"Arquivo salvo em: {output_path}")

    @staticmethod
    def _load_input_file(input_path: Path) -> list[dict]:
        """Load the input championships list or raise a command error."""
        if not input_path.exists():
            raise CommandError(f"Input file not found: {input_path}")

        try:
            with input_path.open(mode="r", encoding="utf-8") as file_obj:
                data = json.load(file_obj)
        except json.JSONDecodeError as exc:
            raise CommandError(f"Invalid JSON in input file {input_path}: {exc}") from exc
        except OSError as exc:
            raise CommandError(f"Could not read input file {input_path}: {exc}") from exc

        if not isinstance(data, list):
            raise CommandError("Input JSON must be a list of championship objects.")

        return data

    @staticmethod
    def _load_output_file(output_path: Path) -> list[dict]:
        """Load existing output data; return an empty list if unavailable or invalid."""
        try:
            with output_path.open(mode="r", encoding="utf-8") as file_obj:
                data = json.load(file_obj)
                if isinstance(data, list):
                    return data
                return []
        except (FileNotFoundError, json.JSONDecodeError, OSError):
            return []

    @staticmethod
    def _save_output_file(output_path: Path, data: list[dict]) -> None:
        """Persist merged championships data as pretty UTF-8 JSON."""
        output_path.parent.mkdir(parents=True, exist_ok=True)

        with output_path.open(mode="w", encoding="utf-8") as file_obj:
            json.dump(data, file_obj, ensure_ascii=False, indent=2)

    @staticmethod
    def _extract_teams(response: SFIChampionshipTeamsResponse, year: int) -> list[dict[str, str]]:
        """Extract the teams list for the selected year from the SFI response."""
        season_payload = response.get("seasons", {}).get(str(year), {})
        teams = season_payload.get("teams", [])
        return [{"id": team.get("id", ""), "name": team.get("name", "")} for team in teams if team.get("id")]
