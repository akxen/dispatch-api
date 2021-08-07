#!/bin/sh

set -e
sleep 5

python manage.py collectstatic --noinput
python manage.py makemigrations
python manage.py migrate
# python manage.py migrate --fake accounts
# python manage.py migrate jobs
python manage.py createsuperuser --noinput || true

# TODO: remove --py-autoreload in production
uwsgi --socket :9000 --master --enable-threads --module project.wsgi --py-autoreload 3
