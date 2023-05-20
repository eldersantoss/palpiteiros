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
    "get_new_matches": {
        "task": "get_new_matches",
        "schedule": crontab(minute="0", hour="0", day_of_week="1,4"),
        "args": (4,),
    },
    "update_matches": {
        "task": "update_matches",
        "schedule": crontab(minute="0", hour="0,1,14-23"),
    },
    "send_email_notification_of_updated_matches": {
        "task": "send_email_notification_of_updated_matches",
        "schedule": crontab(minute="59", hour="18,23"),
    },
    "send_email_notification_of_pending_matches": {
        "task": "send_email_notification_of_pending_matches",
        "schedule": crontab(minute="0", hour="7"),
    },
}


@app.task(bind=True)
def debug_task(self):
    print(f"Request: {self.request!r}")
