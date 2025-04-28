#!/bin/bash

set -x

echo "Начинаем миграцию базы данных..."
python manage.py makemigrations backend
python manage.py migrate
echo "Миграция базы данных успешно завершена!"

echo "Начинаем сборку статических файлов..."
python manage.py collectstatic --noinput
echo "Сборка статических файлов успешно завершена!"

echo "Создаем суперпользователя..."
python manage.py create_superuser

echo "Начинаем запуск сервера..."
gunicorn --bind 0.0.0.0:8000 -w 3 orders.wsgi
