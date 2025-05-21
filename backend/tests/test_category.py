import os
import pytest
from django import setup

# Установка переменной окружения и инициализация Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'orders.settings')
setup()

# Импорты после инициализации Django
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient
from backend.models import Category


# @pytest.mark.django_db
# def test_category_view_get():
#     # Создаем категории
#     category1 = Category.objects.create(name='Category 1')
#     category2 = Category.objects.create(name='Category 2')
#
#     # Выполняем GET-запрос к CategoryView
#     client = APIClient()
#     url = reverse('category-view')
#     response = client.get(url)
#
#     # Проверяем статус код ответа
#     assert response.status_code == status.HTTP_200_OK
#
#     # Проверяем данные ответа
#     expected_data = [
#         {'id': category1.id, 'name': category1.name},
#         {'id': category2.id, 'name': category2.name},
#     ]
#     assert response.json() == expected_data
#
#
# @pytest.mark.django_db
# def test_category_view_get_empty():
#     # Выполняем GET-запрос к CategoryView без категорий
#     client = APIClient()
#     url = reverse('category-view')
#     response = client.get(url)
#
#     # Проверяем статус код ответа
#     assert response.status_code == status.HTTP_200_OK
#
#     # Проверяем данные ответа
#     expected_data = []
#     assert response.json() == expected_data
