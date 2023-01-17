pip install -r requirements.txt
python manage.py migrate
python manage.py createsuperuser_if_none_exists \
    --username=$ADMIN_USERNAME \
    --password=$ADMIN_PASSWORD \
    --email=$ADMIN_EMAIL
python manage.py runserver 0.0.0.0:8000