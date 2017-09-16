#!/bin/bash
python /code/manage.py makemigrations base
python /code/manage.py makemigrations main
python /code/manage.py makemigrations watcher
python /code/manage.py makemigrations api
python /code/manage.py makemigrations
python /code/manage.py migrate auth
python /code/manage.py migrate
python /code/manage.py collectstatic --noinput
uwsgi uwsgi.ini
