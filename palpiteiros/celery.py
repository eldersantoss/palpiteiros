import os

from celery import Celery
from celery.schedules import crontab
from django.conf import settings

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "palpiteiros.settings")

app = Celery("palpiteiros")
app.config_from_object("django.conf:settings", namespace="CELERY")
app.autodiscover_tasks()

app.conf.timezone = settings.TIME_ZONE
app.conf.beat_schedule = {
    "send_email_notification_of_new_matches": {
        "task": "send_email_notification_of_new_matches",
        "schedule": crontab(minute="0", hour="11"),
    },
    "send_email_notification_of_updated_matches": {
        "task": "send_email_notification_of_updated_matches",
        "schedule": crontab(minute="0", hour="7,14,16,22"),
    },
}


@app.task(bind=True)
def debug_task(self):
    print(f"Request: {self.request!r}")
