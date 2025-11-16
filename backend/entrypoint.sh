#!/bin/sh
set -e

python3 manage.py migrate --noinput
python3 manage.py collectstatic --noinput
exec gunicorn config.wsgi:application --bind 0.0.0.0:8000
