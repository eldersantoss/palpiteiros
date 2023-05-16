#!/bin/bash

set -e

PROCESS_TYPE=$1

if [ "$PROCESS_TYPE" = "web" ]; then
  python manage.py migrate
  python manage.py createsuperuser_if_none_exists \
    --username=$ADMIN_USERNAME \
    --password=$ADMIN_PASSWORD \
    --email=$ADMIN_EMAIL
  python manage.py loaddata core/fixtures/competitions_teams_pools_2023.json

  if [ "$DEBUG" = "True" ]; then
    python manage.py runserver 0.0.0.0:$PORT

  else
    python manage.py collectstatic --noinput
    gunicorn \
    --bind 0.0.0.0:$PORT \
    --workers 2 \
    --worker-class gevent \
    --log-level DEBUG \
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

elif [ "$PROCESS_TYPE" = "flower" ]; then
  celery flower
  # celery \
  #   --app dockerapp.celery_app \
  #   flower \
  #   --basic_auth="${CELERY_FLOWER_USER}:${CELERY_FLOWER_PASSWORD}" \
  #   --loglevel INFO
fi
