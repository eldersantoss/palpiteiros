from celery import shared_task
from celery.utils.log import get_task_logger
from django.core.management import call_command

logger = get_task_logger(__name__)


@shared_task(name="send_email_notification_of_new_matches")
def send_email_notification_of_new_matches():
    call_command("send_email_notification_of_new_matches")


@shared_task(name="send_email_notification_of_updated_matches")
def send_email_notification_of_updated_matches():
    call_command("send_email_notification_of_updated_matches")
