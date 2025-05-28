import pytest
from rest_framework.test import APIClient
from rest_framework import status
import time
from django.urls import reverse

@pytest.mark.django_db
def test_login_throttling(api_client, test_token, test_auth_data, create_test_user):
    """Тест throttling для авторизации"""
    # Устанавливаем активность пользователя
    create_test_user.is_active = True
    create_test_user.save()
    
    # Используем аутентифицированный клиент
    api_client.credentials(HTTP_AUTHORIZATION=f'Token {test_token.key}')
    
    url = reverse('backend:user-login')

    # Делаем 5 успешных запросов (предел для auth: 5/hour)
    for i in range(5):
        if i == 0:  # Для первого запроса ждем 2 секунды
            time.sleep(2)
        response = api_client.post(url, test_auth_data)
        assert response.status_code == status.HTTP_200_OK

        # Добавляем небольшую задержку между запросами
        if i < 4:  # Не добавляем задержку после последнего запроса
            time.sleep(1)

    # 6-й запрос должен быть заблокирован
    response = api_client.post(url, test_auth_data)
    assert response.status_code == status.HTTP_429_TOO_MANY_REQUESTS

@pytest.mark.django_db
def test_basket_throttling(api_client, test_token, create_test_user):
    """Тест throttling для корзины"""
    # Устанавливаем токен для аутентификации
    api_client.credentials(HTTP_AUTHORIZATION=f'Token {test_token.key}')

    # Устанавливаем активность пользователя
    create_test_user.is_active = True
    create_test_user.save()

    url = reverse('backend:basket')

    # Делаем 5 успешных запросов (предел для basket: 5/day)
    for i in range(5):
        response = api_client.get(url)
        assert response.status_code == status.HTTP_200_OK

        # Добавляем небольшую задержку между запросами
        if i < 4:  # Не добавляем задержку после последнего запроса
            time.sleep(1)

    # 6-й запрос должен быть заблокирован
    response = api_client.get(url)
    assert response.status_code == status.HTTP_429_TOO_MANY_REQUESTS

@pytest.mark.django_db
def test_throttling_combined(api_client, test_auth_data, test_token, create_test_user):
    """Комбинированный тест throttling для авторизации и корзины"""
    # Устанавливаем активность пользователя
    create_test_user.is_active = True
    create_test_user.save()

    # Сначала проверяем throttling для авторизации
    login_url = reverse('backend:user-login')

    # Делаем 5 успешных запросов авторизации
    for i in range(5):
        if i == 0:  # Для первого запроса ждем 2 секунды
            time.sleep(2)
        response = api_client.post(login_url, test_auth_data)
        assert response.status_code == status.HTTP_200_OK

        # Добавляем небольшую задержку между запросами
        if i < 4:  # Не добавляем задержку после последнего запроса
            time.sleep(1)

    # 6-й запрос авторизации должен быть заблокирован
    response = api_client.post(login_url, test_auth_data)
    assert response.status_code == status.HTTP_429_TOO_MANY_REQUESTS

    # Теперь проверяем throttling для корзины
    api_client.credentials(HTTP_AUTHORIZATION=f'Token {test_token.key}')
    basket_url = reverse('backend:basket')

    # Делаем 5 успешных запросов корзины
    for i in range(5):
        response = api_client.get(basket_url)
        assert response.status_code == status.HTTP_200_OK

        # Добавляем небольшую задержку между запросами
        if i < 4:  # Не добавляем задержку после последнего запроса
            time.sleep(1)

    # 6-й запрос корзины должен быть заблокирован
    response = api_client.get(basket_url)
    assert response.status_code == status.HTTP_429_TOO_MANY_REQUESTS
