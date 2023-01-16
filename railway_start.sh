python manage.py migrate
python manage.py collectstatic --noinput
python manage.py createsuperuser_if_none_exists \
    --username=$ADMIN_USERNAME \
    --password=$ADMIN_PASSWORD \
    --email=$ADMIN_EMAIL
gunicorn \
    --workers 2 \
    --worker-class gevent \
    --log-level DEBUG \
    --access-logfile "-" \
    --error-logfile "-" \
    palpiteiros.wsgi