#!/bin/bash

cd /

if [ $# -eq 0 ]; then
    echo "Usage: start.sh [PROCESS_TYPE](server/beat/worker/flower)"
    exit 1
fi

PROCESS_TYPE=$1

if [ "$PROCESS_TYPE" = "server" ]; then
    if [ "$DEBUG" = "True" ]; then
        python3 manage.py runserver 0.0.0.0:8000
        # gunicorn \
        #     --reload \
        #     --bind 0.0.0.0:8000 \
        #     --workers 2 \
        #     --worker-class gevent \
        #     --log-level DEBUG \
        #     --access-logfile "-" \
        #     --error-logfile "-" \
        #     palpiteiros.wsgi
    else
        gunicorn \
            --bind 0.0.0.0:8000 \
            --workers 2 \
            --worker-class gevent \
            --log-level DEBUG \
            --access-logfile "-" \
            --error-logfile "-" \
            palpiteiros.wsgi
    fi
elif [ "$PROCESS_TYPE" = "beat" ]; then
    celery \
        --app palpiteiros.celery_app \
        beat \
        --loglevel INFO \
        --scheduler django_celery_beat.schedulers:DatabaseScheduler
elif [ "$PROCESS_TYPE" = "flower" ]; then
    celery \
        --app palpiteiros.celery_app \
        flower \
        --basic_auth="${CELERY_FLOWER_USER}:${CELERY_FLOWER_PASSWORD}" \
        --loglevel INFO
elif [ "$PROCESS_TYPE" = "worker" ]; then
    celery \
        --app palpiteiros.celery_app \
        worker \
        --loglevel INFO
fi