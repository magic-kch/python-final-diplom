import pytest
from django.urls import reverse
from rest_framework import status
from backend.models import ConfirmEmailToken, User

@pytest.mark.django_db
def test_password_reset(api_client, test_auth_data, create_test_user):
    """Тест сброса пароля"""
    url = reverse('backend:password-reset')
    response = api_client.post(url, {'email': test_auth_data['email']})
    assert response.status_code == status.HTTP_200_OK
    assert response.json()['message'] == 'Письмо с инструкциями по сбросу пароля отправлено на ваш email'

@pytest.mark.django_db
def test_register_account(api_client):
    """Тест регистрации аккаунта"""
    data = {
        'first_name': 'Test',
        'last_name': 'User',
        'email': 'newuser@example.com',
        'password': 'newpass%:?*JKGKLL',
        'company': 'New Company',
        'position': 'New Position'
    }
    url = reverse('backend:user-register')
    response = api_client.post(url, data)
    # Принимаем как 200, так и 201 как успешные ответы
    assert response.status_code in (status.HTTP_200_OK, status.HTTP_201_CREATED)

@pytest.mark.django_db
def test_get_account_details(api_client, create_test_user):
    """Тест получения деталей аккаунта"""
    # Авторизуемся
    api_client.force_authenticate(user=create_test_user)
    
    url = reverse('backend:user-details')
    response = api_client.get(url)
    assert response.status_code == status.HTTP_200_OK

    # Проверяем, что в ответе есть необходимые поля
    data = response.json()
    assert 'email' in data
    assert 'company' in data
    assert 'position' in data

@pytest.mark.django_db
def test_login_account(api_client, test_auth_data, create_test_user):
    """Тест входа в аккаунт"""
    # Устанавливаем активность пользователя
    create_test_user.is_active = True
    create_test_user.save()
    
    url = reverse('backend:user-login')
    data = {
        'email': test_auth_data['email'],
        'password': test_auth_data['password']
    }
    response = api_client.post(url, data)
    assert response.status_code == status.HTTP_200_OK
    assert response.json()['Status'] is True
    assert 'Token' in response.json()

@pytest.mark.django_db
def test_confirm_account(api_client):
    """Тест подтверждения аккаунта"""
    # Создаем пользователя
    user = User.objects.create_user(
        email='confirm@example.com',
        password='confirm%:?*JKGKLL',
        company='Confirm Company',
        position='Confirm Position'
    )
    user.is_active = False
    user.save()

    # Получаем токен подтверждения
    token = ConfirmEmailToken.objects.create(user=user)

    url = reverse('backend:user-register-confirm')
    data = {
        'email': user.email,
        'token': token.key
    }
    response = api_client.post(url, data)
    assert response.status_code == status.HTTP_200_OK
    assert response.json()['Status'] is True

    # Проверяем, что пользователь активирован
    user.refresh_from_db()
    assert user.is_active is True

@pytest.mark.django_db
def test_category_view(api_client):
    """Тест просмотра категорий"""
    url = reverse('backend:categories')
    response = api_client.get(url)
    assert response.status_code == status.HTTP_200_OK

@pytest.mark.django_db
def test_shop_view(api_client):
    """Тест просмотра магазинов"""
    url = reverse('backend:shops')
    response = api_client.get(url)
    assert response.status_code == status.HTTP_200_OK