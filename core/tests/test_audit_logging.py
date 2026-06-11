import json
import logging
from unittest.mock import patch

import pytest
from django.conf import settings
from django.core.management import call_command
from django.test import override_settings
from django.urls import reverse
from django.utils import timezone
from model_bakery import baker

from core.models import Guess, GuessPool, RankingEntry

pytestmark = pytest.mark.django_db


# Fixture para direcionar os logs de auditoria para um diretório temporário de testes
@pytest.fixture(autouse=True)
def configure_test_logs(settings, tmp_path):
    # Criar subdiretório data/logs no diretório temporário
    (tmp_path / "data" / "logs").mkdir(parents=True, exist_ok=True)
    # Alterar BASE_DIR nas configurações para que o comando acesse a pasta temp
    settings.BASE_DIR = tmp_path

    # Redirecionar o RotatingFileHandler do logger 'guesses_audit'
    logger = logging.getLogger("guesses_audit")
    if logger.handlers:
        handler = logger.handlers[0]
        original_baseFilename = handler.baseFilename
        temp_log_file = tmp_path / "data" / "logs" / "guesses_audit.log"

        handler.close()
        handler.baseFilename = str(temp_log_file)
        handler.stream = handler._open()

        yield temp_log_file

        handler.close()
        handler.baseFilename = original_baseFilename
        handler.stream = handler._open()
    else:
        yield tmp_path / "data" / "logs" / "guesses_audit.log"


# Helpers de Teste
def _make_pool_with_guesser(competition=None):
    guesser = baker.make("core.Guesser")
    pool = baker.make("core.GuessPool", owner=guesser)
    GuessPool.objects.filter(pk=pool.pk).update(created=timezone.now() - timezone.timedelta(days=2))
    pool.refresh_from_db()
    if competition:
        pool.competitions.add(competition)
    return pool, guesser


def _open_match(pool, competition, home_team, away_team):
    return baker.make(
        "core.Match",
        competition=competition,
        home_team=home_team,
        away_team=away_team,
        date_time=timezone.now() + timezone.timedelta(hours=2),
        status="NS",
        home_goals=None,
        away_goals=None,
    )


# --- Testes de Logging e Validação das Views ---


@override_settings(STATICFILES_STORAGE="django.contrib.staticfiles.storage.StaticFilesStorage")
def test_audit_log_saved_on_success(client, configure_test_logs):
    competition = baker.make("core.Competition")
    home_team = baker.make("core.Team", competitions=[competition])
    away_team = baker.make("core.Team", competitions=[competition])
    pool, guesser = _make_pool_with_guesser(competition)
    match = _open_match(pool, competition, home_team, away_team)

    client.force_login(guesser.user)
    response = client.post(
        reverse("core:guesses", kwargs={"pool_slug": pool.slug}),
        {
            "csrfmiddlewaretoken": "dummy",
            f"home_goals_{match.id}": "2",
            f"away_goals_{match.id}": "1",
            "for_all_pools": "on",
        },
    )

    assert response.status_code == 200
    assert pool.guesses.filter(guesser=guesser, match=match).exists()

    # Verificar que o log de auditoria foi gerado com sucesso
    assert configure_test_logs.exists()
    with open(configure_test_logs, "r", encoding="utf-8") as f:
        lines = f.readlines()

    assert len(lines) == 1
    log_data = json.loads(lines[0])
    assert log_data["user"] == guesser.user.username
    assert log_data["pool"] == pool.slug
    assert log_data["action"] == "submit_guesses"
    assert log_data["guesses_submitted"] == {str(match.id): {"home_goals": "2", "away_goals": "1"}}
    assert log_data["results"]["success"] == [match.id]
    assert log_data["error"] is None


@override_settings(STATICFILES_STORAGE="django.contrib.staticfiles.storage.StaticFilesStorage")
def test_audit_log_and_display_error_message_on_guesses_validation_error(client, configure_test_logs):
    competition = baker.make("core.Competition")
    home_team = baker.make("core.Team", competitions=[competition])
    away_team = baker.make("core.Team", competitions=[competition])
    pool, guesser = _make_pool_with_guesser(competition)
    match = _open_match(pool, competition, home_team, away_team)

    client.force_login(guesser.user)
    # Enviar apenas home_goals (inválido, pois deve preencher ambos ou nenhum)
    response = client.post(
        reverse("core:guesses", kwargs={"pool_slug": pool.slug}),
        {
            "csrfmiddlewaretoken": "dummy",
            f"home_goals_{match.id}": "2",
        },
    )

    assert response.status_code == 200
    # O palpite não deve ter sido criado
    assert not pool.guesses.filter(guesser=guesser, match=match).exists()

    # Verificar se as mensagens de erro aparecem no HTML retornado
    html_content = response.content.decode("utf-8")
    assert "form-errors alert alert-danger" in html_content
    assert "Preencha os dois placares ou deixe os dois em branco." in html_content

    # Verificar se gravou no log que houve falha de validação
    with open(configure_test_logs, "r", encoding="utf-8") as f:
        lines = f.readlines()

    assert len(lines) == 1
    log_data = json.loads(lines[0])
    assert log_data["results"]["success"] == []
    assert str(match.id) in log_data["results"]["validation_errors"]
    assert (
        "Preencha os dois placares ou deixe os dois em branco."
        in log_data["results"]["validation_errors"][str(match.id)]
    )


@override_settings(STATICFILES_STORAGE="django.contrib.staticfiles.storage.StaticFilesStorage")
def test_audit_log_and_display_error_message_on_guesses_world_cup_validation_error(client, configure_test_logs):
    competition = baker.make("core.Competition")
    home_team = baker.make("core.Team", competitions=[competition])
    away_team = baker.make("core.Team", competitions=[competition])
    pool, guesser = _make_pool_with_guesser(competition)
    match = _open_match(pool, competition, home_team, away_team)

    client.force_login(guesser.user)
    # Enviar apenas home_goals (inválido, pois deve preencher ambos ou nenhum)
    response = client.post(
        reverse("core:guesses_world_cup", kwargs={"pool_slug": pool.slug}),
        {
            "csrfmiddlewaretoken": "dummy",
            f"home_goals_{match.id}": "2",
        },
    )

    assert response.status_code == 200
    # O palpite não deve ter sido criado
    assert not pool.guesses.filter(guesser=guesser, match=match).exists()

    # Verificar se as mensagens de erro aparecem no HTML retornado
    html_content = response.content.decode("utf-8")
    assert "form-errors alert alert-danger" in html_content
    assert "Preencha os dois placares ou deixe os dois em branco." in html_content

    # Verificar se gravou no log que houve falha de validação
    with open(configure_test_logs, "r", encoding="utf-8") as f:
        lines = f.readlines()

    assert len(lines) == 1
    log_data = json.loads(lines[0])
    assert log_data["results"]["success"] == []
    assert str(match.id) in log_data["results"]["validation_errors"]
    assert (
        "Preencha os dois placares ou deixe os dois em branco."
        in log_data["results"]["validation_errors"][str(match.id)]
    )


@override_settings(STATICFILES_STORAGE="django.contrib.staticfiles.storage.StaticFilesStorage")
@patch("core.models.Guess.objects.create")
def test_audit_log_written_on_database_exception(mock_create, client, configure_test_logs):
    mock_create.side_effect = RuntimeError("Erro crítico de banco de dados")

    competition = baker.make("core.Competition")
    home_team = baker.make("core.Team", competitions=[competition])
    away_team = baker.make("core.Team", competitions=[competition])
    pool, guesser = _make_pool_with_guesser(competition)
    match = _open_match(pool, competition, home_team, away_team)

    client.force_login(guesser.user)

    with pytest.raises(RuntimeError):
        client.post(
            reverse("core:guesses", kwargs={"pool_slug": pool.slug}),
            {
                "csrfmiddlewaretoken": "dummy",
                f"home_goals_{match.id}": "2",
                f"away_goals_{match.id}": "1",
            },
        )

    # O log de auditoria DEVE conter a exceção no campo 'error'
    assert configure_test_logs.exists()
    with open(configure_test_logs, "r", encoding="utf-8") as f:
        lines = f.readlines()

    assert len(lines) == 1
    log_data = json.loads(lines[0])
    assert log_data["error"] == "Erro crítico de banco de dados"


# --- Testes do Comando CLI restore_guesses ---


def test_restore_guesses_command_success(settings, configure_test_logs):
    competition = baker.make("core.Competition")
    home_team = baker.make("core.Team", competitions=[competition])
    away_team = baker.make("core.Team", competitions=[competition])
    pool, guesser = _make_pool_with_guesser(competition)
    match = _open_match(pool, competition, home_team, away_team)

    # Escrever entrada no log temporário
    log_entry = {
        "timestamp": "2026-06-10T15:30:00.000000",
        "user": guesser.user.username,
        "pool": pool.slug,
        "action": "submit_guesses",
        "for_all_pools": True,
        "guesses_submitted": {str(match.id): {"home_goals": "3", "away_goals": "2"}},
        "results": {"success": [match.id], "validation_errors": {}, "match_closed": []},
        "error": None,
    }
    with open(configure_test_logs, "w", encoding="utf-8") as f:
        f.write(json.dumps(log_entry) + "\n")

    # Executar o comando
    call_command(
        "restore_guesses", username=guesser.user.username, pool=pool.slug, date="2026-06-10", non_interactive=True
    )

    # Validar palpite criado no banco
    assert pool.guesses.filter(guesser=guesser, match=match).exists()
    guess = pool.guesses.get(guesser=guesser, match=match)
    assert guess.home_goals == 3
    assert guess.away_goals == 2


def test_restore_guesses_command_skip_invalid(settings, configure_test_logs):
    competition = baker.make("core.Competition")
    home_team = baker.make("core.Team", competitions=[competition])
    away_team = baker.make("core.Team", competitions=[competition])
    pool, guesser = _make_pool_with_guesser(competition)
    match = _open_match(pool, competition, home_team, away_team)

    # Gravar palpite incompleto/inválido no log
    log_entry = {
        "timestamp": "2026-06-10T15:30:00.000000",
        "user": guesser.user.username,
        "pool": pool.slug,
        "action": "submit_guesses",
        "for_all_pools": True,
        "guesses_submitted": {str(match.id): {"home_goals": "3", "away_goals": ""}},  # away_goals vazio
        "results": {},
        "error": None,
    }
    with open(configure_test_logs, "w", encoding="utf-8") as f:
        f.write(json.dumps(log_entry) + "\n")

    call_command(
        "restore_guesses", username=guesser.user.username, pool=pool.slug, date="2026-06-10", non_interactive=True
    )

    # O palpite NÃO deve ser inserido
    assert not pool.guesses.filter(guesser=guesser, match=match).exists()


def test_restore_guesses_command_updates_existing_when_goals_differ(settings, configure_test_logs):
    competition = baker.make("core.Competition")
    home_team = baker.make("core.Team", competitions=[competition])
    away_team = baker.make("core.Team", competitions=[competition])
    pool, guesser = _make_pool_with_guesser(competition)
    match = _open_match(pool, competition, home_team, away_team)

    # Palpite já existe no banco com 0x0
    existing = Guess.objects.create(guesser=guesser, match=match, home_goals=0, away_goals=0)
    pool.guesses.add(existing)

    log_entry = {
        "timestamp": "2026-06-10T15:30:00.000000",
        "user": guesser.user.username,
        "pool": pool.slug,
        "action": "submit_guesses",
        "for_all_pools": True,
        "guesses_submitted": {str(match.id): {"home_goals": "4", "away_goals": "4"}},
        "results": {},
        "error": None,
    }
    with open(configure_test_logs, "w", encoding="utf-8") as f:
        f.write(json.dumps(log_entry) + "\n")

    call_command(
        "restore_guesses", username=guesser.user.username, pool=pool.slug, date="2026-06-10", non_interactive=True
    )

    # Deve atualizar o palpite antigo no banco para 4x4
    db_guess = pool.guesses.get(guesser=guesser, match=match)
    assert db_guess.home_goals == 4
    assert db_guess.away_goals == 4


def test_restore_guesses_command_skip_existing_when_goals_are_identical(settings, configure_test_logs):
    competition = baker.make("core.Competition")
    home_team = baker.make("core.Team", competitions=[competition])
    away_team = baker.make("core.Team", competitions=[competition])
    pool, guesser = _make_pool_with_guesser(competition)
    match = _open_match(pool, competition, home_team, away_team)

    # Palpite já existe no banco com 1x2
    existing = Guess.objects.create(guesser=guesser, match=match, home_goals=1, away_goals=2)
    pool.guesses.add(existing)

    log_entry = {
        "timestamp": "2026-06-10T15:30:00.000000",
        "user": guesser.user.username,
        "pool": pool.slug,
        "action": "submit_guesses",
        "for_all_pools": True,
        "guesses_submitted": {str(match.id): {"home_goals": "1", "away_goals": "2"}},
        "results": {},
        "error": None,
    }
    with open(configure_test_logs, "w", encoding="utf-8") as f:
        f.write(json.dumps(log_entry) + "\n")

    call_command(
        "restore_guesses", username=guesser.user.username, pool=pool.slug, date="2026-06-10", non_interactive=True
    )

    # Mantém os valores e não faz nova transação/atualização
    db_guess = pool.guesses.get(guesser=guesser, match=match)
    assert db_guess.home_goals == 1
    assert db_guess.away_goals == 2


def test_restore_guesses_command_retroactive_consolidation(settings, configure_test_logs):
    competition = baker.make("core.Competition")
    home_team = baker.make("core.Team", competitions=[competition])
    away_team = baker.make("core.Team", competitions=[competition])
    pool, guesser = _make_pool_with_guesser(competition)

    # Partida encerrada com placar 2x1
    match = baker.make(
        "core.Match",
        competition=competition,
        home_team=home_team,
        away_team=away_team,
        date_time=timezone.now() - timezone.timedelta(hours=5),
        status="FT",
        home_goals=2,
        away_goals=1,
    )

    log_entry = {
        "timestamp": "2026-06-10T15:30:00.000000",
        "user": guesser.user.username,
        "pool": pool.slug,
        "action": "submit_guesses",
        "for_all_pools": True,
        "guesses_submitted": {str(match.id): {"home_goals": "2", "away_goals": "1"}},  # Cravou placar
        "results": {},
        "error": None,
    }
    with open(configure_test_logs, "w", encoding="utf-8") as f:
        f.write(json.dumps(log_entry) + "\n")

    call_command(
        "restore_guesses", username=guesser.user.username, pool=pool.slug, date="2026-06-10", non_interactive=True
    )

    # Validar se o palpite foi criado, consolidado com sucesso e os rankings recalculados (+10 pontos)
    guess = pool.guesses.get(guesser=guesser, match=match)
    assert guess.home_goals == 2
    assert guess.away_goals == 1
    assert guess.consolidated is True
    assert guess.score == 10

    # Verificar se as tabelas de ranking possuem os 10 pontos
    ranking_entry = RankingEntry.objects.get(pool=pool, guesser=guesser, year=0, month=0, week=0)
    assert ranking_entry.score == 10


def test_restore_guesses_command_rotated_logs(settings, configure_test_logs):
    competition = baker.make("core.Competition")
    home_team = baker.make("core.Team", competitions=[competition])
    away_team = baker.make("core.Team", competitions=[competition])
    pool, guesser = _make_pool_with_guesser(competition)
    match = _open_match(pool, competition, home_team, away_team)

    # Simular rotação: colocar a tentativa em guesses_audit.log.1
    log_entry = {
        "timestamp": "2026-06-10T15:30:00.000000",
        "user": guesser.user.username,
        "pool": pool.slug,
        "action": "submit_guesses",
        "for_all_pools": True,
        "guesses_submitted": {str(match.id): {"home_goals": "1", "away_goals": "2"}},
        "results": {},
        "error": None,
    }

    # Criar guesses_audit.log.1 no diretório temporário
    rotated_path = settings.BASE_DIR / "data" / "logs" / "guesses_audit.log.1"
    with open(rotated_path, "w", encoding="utf-8") as f:
        f.write(json.dumps(log_entry) + "\n")

    call_command(
        "restore_guesses", username=guesser.user.username, pool=pool.slug, date="2026-06-10", non_interactive=True
    )

    # Validar palpite recuperado com sucesso do log rotacionado
    assert pool.guesses.filter(guesser=guesser, match=match).exists()
    guess = pool.guesses.get(guesser=guesser, match=match)
    assert guess.home_goals == 1
    assert guess.away_goals == 2
