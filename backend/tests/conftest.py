import os
import pytest
from django import setup
from django.contrib.auth import get_user_model
from rest_framework.authtoken.models import Token
from rest_framework.test import APIClient
from django.core.cache import cache
from backend.models import (Order, OrderItem, Contact,
                            Shop, Category, Product, ProductInfo)

User = get_user_model()

@pytest.fixture(scope='session', autouse=True)
def setup_django():
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'orders.settings')
    setup()

@pytest.fixture
def create_test_user():
    """Фикстура для создания тестового пользователя"""
    user = User.objects.create_user(
        email='test@example.com',
        password='testpass%:?*JKGKLL',
        company='Test Company',
        position='Test Position'
    )
    return user

@pytest.fixture
def test_auth_data():
    """Фикстура для данных аутентификации"""
    return {
        'email': 'test@example.com',
        'password': 'testpass%:?*JKGKLL'
    }

@pytest.fixture
def test_token(create_test_user):
    """Фикстура для токена аутентификации"""
    token = Token.objects.create(user=create_test_user)
    return token

@pytest.fixture
def api_client():
    """Фикстура для создания клиента API"""
    return APIClient()

@pytest.fixture(autouse=True)
def reset_throttles():
    """Фикстура для сброса тротлинга между тестами"""
    cache.clear()

@pytest.fixture
def create_shop():
    """Фикстура для создания тестового магазина"""
    shop = Shop.objects.create(
        name='Test Shop',
        url='http://testshop.com'
    )
    return shop

@pytest.fixture
def create_product(create_shop):
    """Фикстура для создания тестового продукта"""
    category = Category.objects.create(name='Test Category')
    product = Product.objects.create(
        name='Test Product',
        category=category
    )
    product_info = ProductInfo.objects.create(
        product=product,
        shop=create_shop,
        price=1000,
        quantity=100,
        external_id=1,
        price_rrc=1200
    )
    return product_info

@pytest.fixture
def create_user_shop(create_test_user, create_shop):
    """Фикстура для создания магазина для пользователя"""
    # Сначала создаем пользователя с типом 'shop'
    create_test_user.type = 'shop'
    create_test_user.is_active = True
    create_test_user.save()
    
    # Создаем магазин для этого пользователя
    shop = Shop.objects.create(
        name='Test Shop',
        user=create_test_user,
        state=True
    )
    return shop

@pytest.fixture
def create_contact(create_test_user):
    """Фикстура для создания тестового контакта"""
    contact = Contact.objects.create(
        user=create_test_user,
        city='Test City',
        street='Test Street',
        house='1',
        phone='+79000000000'
    )
    return contact

@pytest.fixture
def create_order(create_test_user, create_contact):
    """Фикстура для создания тестового заказа"""
    order = Order.objects.create(
        user=create_test_user,
        contact=create_contact,
        state='new'
    )
    return order

@pytest.fixture
def create_order_item(create_order, create_product):
    """Фикстура для создания тестового товара в заказе"""
    order_item = OrderItem.objects.create(
        order=create_order,
        product_info=create_product,
        quantity=5
    )
    return order_item
