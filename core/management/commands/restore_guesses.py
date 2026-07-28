import json
import os
from datetime import datetime

from django.conf import settings
from django.contrib.auth.models import User
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.utils import timezone

from core.models import Guess, Guesser, GuessPool, Match


class Command(BaseCommand):
    help = (
        "Restaura palpites válidos de um usuário para um bolão a partir dos logs de auditoria de uma determinada data."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--username", type=str, required=True, help="Username do usuário a ter palpites restaurados"
        )
        parser.add_argument("--pool", type=str, required=True, help="Slug do bolão")
        parser.add_argument(
            "--date", type=str, required=False, help="Data do envio no formato YYYY-MM-DD (padrão: data de hoje)"
        )
        parser.add_argument(
            "--non-interactive",
            action="store_true",
            help="Desativa o prompt interativo e seleciona automaticamente a tentativa mais recente.",
        )

    def find_matching_logs(self, username, pool_slug, date_str):
        log_files = [settings.BASE_DIR / "data" / "logs" / "guesses_audit.log"]
        for i in range(1, 6):
            backup = settings.BASE_DIR / "data" / "logs" / f"guesses_audit.log.{i}"
            if os.path.exists(backup):
                log_files.append(backup)

        matching_entries = []
        for log_path in log_files:
            if not os.path.exists(log_path):
                continue
            with open(log_path, "r", encoding="utf-8") as f:
                for line in f:
                    if not line.strip():
                        continue
                    try:
                        entry = json.loads(line)
                        entry_user = entry.get("user")
                        entry_pool = entry.get("pool")
                        entry_timestamp = entry.get("timestamp")

                        if not entry_user or not entry_pool or not entry_timestamp:
                            continue

                        if entry_user.lower() != username.lower():
                            continue
                        if entry_pool != pool_slug:
                            continue

                        entry_date = entry_timestamp.split("T")[0]
                        if entry_date != date_str:
                            continue

                        matching_entries.append(entry)
                    except Exception:
                        continue

        # Ordenar por timestamp decrescente (mais recente primeiro)
        matching_entries.sort(key=lambda x: x.get("timestamp", ""), reverse=True)
        return matching_entries

    def handle(self, *args, **options):
        username = options["username"]
        pool_slug = options["pool"]
        interactive = not options["non_interactive"]

        if not options.get("date"):
            date_str = timezone.localdate().strftime("%Y-%m-%d")
        else:
            date_str = options["date"]
            # Validar formato da data
            try:
                datetime.strptime(date_str, "%Y-%m-%d")
            except ValueError:
                raise CommandError("O formato da data deve ser YYYY-MM-DD.")

        # Buscar Usuário e Guesser
        try:
            user = User.objects.get(username__iexact=username)
        except User.DoesNotExist:
            raise CommandError(f"Usuário '{username}' não encontrado.")

        try:
            guesser = user.guesser
        except Guesser.DoesNotExist:
            raise CommandError(f"O usuário '{username}' não possui um perfil de palpiteiro (Guesser) associado.")

        # Buscar Bolão
        try:
            pool = GuessPool.objects.get(slug=pool_slug)
        except GuessPool.DoesNotExist:
            raise CommandError(f"Bolão com slug '{pool_slug}' não encontrado.")

        # Buscar entradas nos logs
        self.stdout.write(f"Buscando submissões nos logs para '{username}' no bolão '{pool_slug}' em {date_str}...")
        matching_entries = self.find_matching_logs(username, pool_slug, date_str)

        if not matching_entries:
            raise CommandError(
                f"Nenhuma submissão de palpite foi encontrada para o usuário '{username}' no bolão '{pool_slug}' em {date_str}."
            )

        selected_entry = None
        if len(matching_entries) > 1 and interactive:
            self.stdout.write(f"Foram encontradas {len(matching_entries)} submissões de palpites:")
            for i, entry in enumerate(matching_entries):
                ts = entry.get("timestamp")
                guesses = entry.get("guesses_submitted", {})
                guesses_summary = ", ".join(
                    f"Match {m_id}: {g.get('home_goals')}x{g.get('away_goals')}" for m_id, g in guesses.items()
                )
                self.stdout.write(f" [{i+1}] Horário: {ts} | Palpites: {guesses_summary}")

            choice = None
            while choice is None:
                try:
                    raw_choice = input(f"Selecione qual submissão deseja restaurar (1-{len(matching_entries)}): ")
                    idx = int(raw_choice) - 1
                    if 0 <= idx < len(matching_entries):
                        choice = matching_entries[idx]
                    else:
                        self.stdout.write("Opção inválida. Escolha um número válido da lista.")
                except ValueError:
                    self.stdout.write("Por favor, digite um número inteiro.")
                except (EOFError, KeyboardInterrupt):
                    self.stdout.write("\nEntrada cancelada. Assumindo a submissão mais recente.")
                    choice = matching_entries[0]
            selected_entry = choice
        else:
            selected_entry = matching_entries[0]

        guesses_submitted = selected_entry.get("guesses_submitted", {})
        for_all_pools = selected_entry.get("for_all_pools", True)

        self.stdout.write(f"Iniciando restauração a partir do envio de: {selected_entry.get('timestamp')}")

        has_new_guesses = False
        restored_count = 0
        skipped_invalid = 0
        skipped_existing = 0

        for match_id_str, g_data in guesses_submitted.items():
            try:
                match_id = int(match_id_str)
                match = Match.objects.get(id=match_id)
            except (ValueError, Match.DoesNotExist):
                self.stdout.write(self.style.WARNING(f"Partida ID {match_id_str} não encontrada. Pulando."))
                continue

            home_goals_raw = g_data.get("home_goals")
            away_goals_raw = g_data.get("away_goals")

            # Validação: impede restauração de dados inválidos (em branco, vazios ou negativos)
            if (
                home_goals_raw is None
                or away_goals_raw is None
                or str(home_goals_raw).strip() == ""
                or str(away_goals_raw).strip() == ""
            ):
                self.stdout.write(
                    self.style.WARNING(f"Palpite para partida '{match}' (ID {match_id}) incompleto. Pulando.")
                )
                skipped_invalid += 1
                continue

            try:
                home_goals = int(home_goals_raw)
                away_goals = int(away_goals_raw)
                if home_goals < 0 or away_goals < 0:
                    raise ValueError("Goals must be non-negative")
            except ValueError:
                self.stdout.write(
                    self.style.WARNING(
                        f"Gols inválidos para partida '{match}' (ID {match_id}): {home_goals_raw}x{away_goals_raw}. Pulando."
                    )
                )
                skipped_invalid += 1
                continue

            # Verificar se palpite já existe no banco
            existing_guess = pool.guesses.filter(match=match, guesser=guesser).first()
            if existing_guess:
                if existing_guess.home_goals == home_goals and existing_guess.away_goals == away_goals:
                    self.stdout.write(
                        f"Palpite para a partida '{match}' (ID {match_id}) já está atualizado com {home_goals}x{away_goals}. Pulando."
                    )
                    skipped_existing += 1
                    continue
                else:
                    with transaction.atomic():
                        previous_home = existing_guess.home_goals
                        previous_away = existing_guess.away_goals
                        existing_guess.home_goals = home_goals
                        existing_guess.away_goals = away_goals
                        existing_guess.save()
                        pool.add_guess_to_pools(existing_guess, for_all_pools)
                        has_new_guesses = True
                        restored_count += 1

                        if match.result_str is not None:
                            previous_score = existing_guess.score
                            existing_guess.evaluate_and_consolidate()
                            self.stdout.write(
                                self.style.SUCCESS(
                                    f"Atualizado e Consolidado: '{match}' -> {home_goals}x{away_goals} (Anterior: {previous_home}x{previous_away} | Resultado Oficial: {match.result_str} | Pontuação: {previous_score} -> {existing_guess.score} PTS)"
                                )
                            )
                        else:
                            self.stdout.write(
                                self.style.SUCCESS(
                                    f"Atualizado (Aberta): '{match}' -> {home_goals}x{away_goals} (Anterior: {previous_home}x{previous_away})"
                                )
                            )
                    continue

            # Gravar palpite no banco de dados e aplicar regras do bolão
            with transaction.atomic():
                guess = Guess.objects.create(
                    match=match,
                    guesser=guesser,
                    home_goals=home_goals,
                    away_goals=away_goals,
                )
                pool.add_guess_to_pools(guess, for_all_pools)
                has_new_guesses = True
                restored_count += 1

                # Se a partida já estiver finalizada, re-calcular os rankings do usuário
                if match.result_str is not None:
                    guess.evaluate_and_consolidate()
                    self.stdout.write(
                        self.style.SUCCESS(
                            f"Restaurado e Consolidado: '{match}' -> {home_goals}x{away_goals} (Resultado Oficial: {match.result_str} | Pontuação: {guess.score} PTS)"
                        )
                    )
                else:
                    self.stdout.write(
                        self.style.SUCCESS(f"Restaurado (Aberta): '{match}' -> {home_goals}x{away_goals}")
                    )

        if has_new_guesses:
            pool.delete_orphans_guesses()

        self.stdout.write(
            self.style.SUCCESS(
                f"Processamento concluído. Restaurados: {restored_count} | Pulados inválidos: {skipped_invalid} | Pulados já existentes: {skipped_existing}."
            )
        )
