#!/bin/bash

set -x

echo "Начинаем миграцию базы данных..."
python manage.py migrate
echo "Миграция базы данных успешно завершена!"

echo "Начинаем сборку статических файлов..."
python manage.py collectstatic --noinput
echo "Сборка статических файлов успешно завершена!"

echo "Создаем суперпользователя..."
#TO_DO python manage.py createsuperuser --email admin@admin.ru --skip-checks

echo "Начинаем запуск сервера..."
gunicorn --bind 0.0.0.0:8000 -w 3 orders.wsgi