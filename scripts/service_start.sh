#!/bin/bash

set -e

PROCESS_TYPE=$1

if [ "$PROCESS_TYPE" = "web" ]; then
  python manage.py migrate
  python manage.py createsuperuser_if_none_exists \
    --username=$ADMIN_USERNAME \
    --password=$ADMIN_PASSWORD \
    --email=$ADMIN_EMAIL

  if [ "$DEBUG" = "True" ]; then
    python manage.py runserver 0.0.0.0:$PORT

  else
    python manage.py collectstatic --noinput
    gunicorn \
    --bind 0.0.0.0:$PORT \
    --workers $NUM_WORKERS \
    --worker-class gevent \
    --log-level $LOG_LEVEL \
    --access-logfile "-" \
    --error-logfile "-" \
    palpiteiros.wsgi
  fi

elif [ "$PROCESS_TYPE" = "worker" ]; then
  celery -A palpiteiros worker -l info

elif [ "$PROCESS_TYPE" = "beat" ]; then
  celery -A palpiteiros beat -l info

elif [ "$PROCESS_TYPE" = "worker_beat" ]; then
  celery -A palpiteiros worker --beat -l info

elif [ "$PROCESS_TYPE" = "create_and_update_matches" ]; then
  python manage.py create_and_update_matches

elif [ "$PROCESS_TYPE" = "sync_sfi_matches" ]; then
  python manage.py sync_sfi_matches

elif [ "$PROCESS_TYPE" = "sync_sfi_world_cup_matches" ]; then
  python manage.py sync_sfi_world_cup_matches
fi
