from celery import shared_task
from celery.utils.log import get_task_logger
from django.core.management import call_command

logger = get_task_logger(__name__)


@shared_task(name="get_competitions")
def get_competitions(season: int, league_ids: list[int]):
    call_command("get_competitions", season, league_ids)


@shared_task(name="get_new_matches")
def get_new_matches(days_ahead: int):
    call_command("get_new_matches", days_ahead)


@shared_task(name="update_matches")
def update_matches():
    call_command("update_matches")


@shared_task(name="send_email_notification_of_new_matches")
def send_email_notification_of_new_matches():
    call_command("send_email_notification_of_new_matches")


@shared_task(name="send_email_notification_of_updated_matches")
def send_email_notification_of_updated_matches():
    call_command("send_email_notification_of_updated_matches")


@shared_task(name="send_email_notification_of_pending_matches")
def send_email_notification_of_pending_matches():
    call_command("send_email_notification_of_pending_matches")
