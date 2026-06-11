import json
import logging

from django.utils import timezone

# Obter o logger de auditoria configurado
audit_logger = logging.getLogger("guesses_audit")


def log_guess_submission(
    user, guesser, pool, for_all_pools, action, guesses_submitted, results=None, error=None, request=None
):
    """
    Registra os dados simplificados de submissão de palpites no log de auditoria guesses_audit.
    """
    log_entry = {
        "timestamp": timezone.now().isoformat(),
        "user": user.username if user else None,
        "user_id": user.id if user else None,
        "pool": pool.slug if pool else None,
        "action": action,
        "for_all_pools": for_all_pools,
        "guesses_submitted": guesses_submitted,
        "results": results or {"success": [], "validation_errors": {}, "match_closed": []},
        "error": str(error) if error else None,
    }

    # Grava a linha formatada em JSON no log de auditoria
    audit_logger.info(json.dumps(log_entry, ensure_ascii=False))
