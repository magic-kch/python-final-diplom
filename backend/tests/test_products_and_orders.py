import pytest
from django.urls import reverse
from rest_framework import status
from backend.models import Contact, Order
from django.core.files.uploadedfile import SimpleUploadedFile

@pytest.mark.django_db
def test_product_search(api_client, create_product):
    """Тест поиска товаров"""
    # Проверяем поиск по названию продукта
    url = reverse('backend:product-info')
    response = api_client.get(url, {'product': 'Test'})
    assert response.status_code == status.HTTP_200_OK
    assert len(response.json()) > 0

    # Проверяем поиск по магазину
    response = api_client.get(url, {'shop_id': create_product.shop.id})
    assert response.status_code == status.HTTP_200_OK
    assert len(response.json()) > 0

    # Проверяем диапазон цен
    response = api_client.get(url, {'price_min': 500, 'price_max': 1500})
    assert response.status_code == status.HTTP_200_OK
    assert len(response.json()) > 0

@pytest.mark.django_db
def test_basket_operations(api_client, test_token, create_test_user, create_product):
    """Тест операций с корзиной"""
    # Устанавливаем активность пользователя
    create_test_user.is_active = True
    create_test_user.save()
    
    # Авторизуемся
    api_client.credentials(HTTP_AUTHORIZATION=f'Token {test_token.key}')
    
    # Добавляем товар в корзину
    url = reverse('backend:basket')
    data = {
        'items': f'[{{"product_info": {create_product.id}, "quantity": 2}}]'
    }
    response = api_client.post(url, data)
    assert response.status_code == status.HTTP_200_OK
    assert response.json()['Status'] is True
    assert response.json()['Создано объектов'] == 1

    # Обновляем количество товара
    data = {
        'items': f'[{{"id": 1, "quantity": 3}}]'
    }
    response = api_client.put(url, data)
    assert response.status_code == status.HTTP_200_OK
    assert response.json()['Status'] is True
    assert response.json()['Обновлено объектов'] == 1

    # Удаляем товар из корзины
    data = {'items': '1'}
    response = api_client.delete(url, data)
    assert response.status_code == status.HTTP_200_OK
    assert response.json()['Status'] is True
    assert response.json()['Удалено объектов'] == 1

@pytest.mark.django_db
def test_partner_operations(api_client, test_token, create_test_user, create_user_shop):
    """Тест операций с партнёром"""
    # Устанавливаем активность пользователя и тип магазина
    create_test_user.is_active = True
    create_test_user.type = 'shop'
    create_test_user.save()
    
    # Авторизуемся
    api_client.credentials(HTTP_AUTHORIZATION=f'Token {test_token.key}')
    
    # Проверяем получение статуса
    url = reverse('backend:partner-state')
    response = api_client.get(url)
    assert response.status_code == status.HTTP_200_OK

    # Меняем статус магазина
    data = {'state': 'true'}
    response = api_client.post(url, data)
    assert response.status_code == status.HTTP_200_OK
    assert response.json()['Status'] is True

    # Проверяем обновление прайса
    url = reverse('backend:partner-update')
    # Создаем тестовый файл
    test_file = SimpleUploadedFile(
        'test.yaml',
        b'products: []',
        content_type='application/yaml'
    )
    data = {
        'url': 'http://testshop.com/prices.yaml',
        'file': test_file
    }
    response = api_client.post(url, data, format='multipart')
    assert response.status_code == status.HTTP_202_ACCEPTED
    assert response.json()['Status'] is True

@pytest.mark.django_db
def test_contact_operations(api_client, test_token, create_test_user):
    """Тест операций с контактами"""
    # Устанавливаем активность пользователя
    create_test_user.is_active = True
    create_test_user.save()
    
    # Авторизуемся
    api_client.credentials(HTTP_AUTHORIZATION=f'Token {test_token.key}')
    
    # Получаем контакты
    url = reverse('backend:contact')
    response = api_client.get(url)
    assert response.status_code == status.HTTP_200_OK

    # Создаем контакт
    data = {
        'city': 'New City',
        'street': 'New Street',
        'phone': '+79001111111'
    }
    response = api_client.post(url, data)
    assert response.status_code == status.HTTP_200_OK
    assert response.json()['Status'] is True

    # Обновляем контакт
    contact_id = Contact.objects.filter(user=create_test_user).first().id
    data = {
        'id': contact_id,
        'city': 'Updated City'
    }
    response = api_client.put(url, data)
    assert response.status_code == status.HTTP_200_OK
    assert response.json()['Status'] is True

    # Удаляем контакт
    data = {'items': str(contact_id)}
    response = api_client.delete(url, data)
    assert response.status_code == status.HTTP_200_OK
    assert response.json()['Status'] is True

@pytest.mark.django_db
def test_order_operations(api_client, test_token, create_test_user, create_contact, create_product):
    """Тест операций с заказами"""
    # Устанавливаем активность пользователя
    create_test_user.is_active = True
    create_test_user.type = 'buyer'
    create_test_user.save()
    
    # Авторизуемся
    api_client.credentials(HTTP_AUTHORIZATION=f'Token {test_token.key}')
    
    # Получаем заказы
    url = reverse('backend:order')
    response = api_client.get(url)
    assert response.status_code == status.HTTP_200_OK

    # Добавляем товар в корзину
    basket_url = reverse('backend:basket')
    basket_data = {
        'items': f'[{{"product_info": {create_product.id}, "quantity": 2}}]'
    }
    response = api_client.post(basket_url, basket_data)
    assert response.status_code == status.HTTP_200_OK
    assert response.json()['Status'] is True

    # Получаем корзину
    basket = Order.objects.filter(
        user=create_test_user,
        state='basket'
    ).first()
    assert basket is not None

    # Создаем заказ
    order_data = {
        'id': basket.id,
        'contact': create_contact.id
    }
    response = api_client.post(url, order_data)
    assert response.status_code == status.HTTP_200_OK
    assert response.json()['Status'] is True

    # Проверяем, что заказ создан
    order = Order.objects.filter(
        user=create_test_user,
        state='new'
    ).first()
    assert order is not None
    assert order.contact == create_contact
