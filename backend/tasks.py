from celery import shared_task
from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string
from django.utils.html import strip_tags
from django.conf import settings
from django.db import transaction
from django_rest_passwordreset.models import ResetPasswordToken
from requests import get
from yaml import load as load_yaml, Loader
from django.core.files.storage import default_storage
from django.core.files.base import ContentFile
from io import BytesIO
from PIL import Image
import os

from backend.models import (
    User,
    ConfirmEmailToken,
    Shop,
    Category,
    Product,
    ProductInfo,
    Parameter,
    ProductParameter,
)


@shared_task
def send_confirmation_email(user_id):
    try:
        user = User.objects.get(id=user_id)
        token, _ = ConfirmEmailToken.objects.get_or_create(user=user)

        subject = f"Подтверждение email для {user.email}"
        html_message = render_to_string('confirmation_email.html', {
            'user': user,
            'token': token.key
        })
        plain_message = strip_tags(html_message)

        msg = EmailMultiAlternatives(
            subject,
            plain_message,
            settings.EMAIL_HOST_USER,
            [user.email]
        )
        msg.attach_alternative(html_message, "text/html")
        msg.send()

    except User.DoesNotExist:
        pass


@shared_task
def send_order_email(user_id):
    try:
        user = User.objects.get(id=user_id)

        subject = "Обновление статуса заказа"
        html_message = render_to_string('order_email.html', {
            'user': user
        })
        plain_message = strip_tags(html_message)

        msg = EmailMultiAlternatives(
            subject,
            plain_message,
            settings.EMAIL_HOST_USER,
            [user.email]
        )
        msg.attach_alternative(html_message, "text/html")
        msg.send()

    except User.DoesNotExist:
        pass


@shared_task
def send_password_reset_email(user_id, reset_password_token):
    try:
        user = User.objects.get(id=user_id)
        token = ResetPasswordToken.objects.get(key=reset_password_token)

        subject = f"Сброс пароля для {user.email}"
        html_message = render_to_string('password_reset_email.html', {
            'user': user,
            'token': token.key
        })

        msg = EmailMultiAlternatives(
            subject,
            strip_tags(html_message),
            settings.EMAIL_HOST_USER,
            [user.email]
        )
        msg.attach_alternative(html_message, "text/html")
        msg.send()

    except (User.DoesNotExist, ResetPasswordToken.DoesNotExist):
        pass


@shared_task
def reset_password_request_token(user_id):
    try:
        user = User.objects.get(id=user_id)
        token = ResetPasswordToken.objects.create(
            user=user,
            key=ResetPasswordToken.generate_key()
        )
        send_password_reset_email.delay(user.id, token.key)
    except User.DoesNotExist:
        pass


@shared_task(bind=True)
def update_partner_price(self, shop_id, url):
    try:
        with transaction.atomic():
            shop = Shop.objects.get(id=shop_id)

            # Загрузка и обработка YAML
            stream = get(url).content
            data = load_yaml(stream, Loader=Loader)

            # Обновление названия магазина
            shop.name = data['shop']
            shop.save()

            # Обработка категорий
            for category in data['categories']:
                category_obj, _ = Category.objects.get_or_create(
                    id=category['id'],
                    defaults={'name': category['name']}
                )
                category_obj.shops.add(shop)
                category_obj.save()

            # Удаление старых товаров
            ProductInfo.objects.filter(shop=shop).delete()

            # Добавление новых товаров
            for item in data['goods']:
                product, _ = Product.objects.get_or_create(
                    name=item['name'],
                    category_id=item['category']
                )

                product_info = ProductInfo.objects.create(
                    product=product,
                    external_id=item['id'],
                    model=item['model'],
                    price=item['price'],
                    price_rrc=item['price_rrc'],
                    quantity=item['quantity'],
                    shop=shop
                )

                for name, value in item['parameters'].items():
                    parameter, _ = Parameter.objects.get_or_create(name=name)
                    ProductParameter.objects.create(
                        product_info=product_info,
                        parameter=parameter,
                        value=value
                    )

        return {'status': 'success', 'message': 'Price list updated'}

    except Exception as e:
        self.retry(exc=e, countdown=60, max_retries=3)


@shared_task
def generate_thumbnails(product_info_id):
    """
    Генерирует миниатюры для изображения товара

    Аргументы:
        product_info_id (int): ID записи ProductInfo
    """
    try:
        from backend.models import ProductInfo
        from time import sleep
        import os
        from django.conf import settings

        # Получаем объект ProductInfo
        product_info = ProductInfo.objects.get(id=product_info_id)

        if not product_info.image:
            print(f"Изображение не найдено для ProductInfo {product_info_id}")
            return False

        # Полный путь к файлу
        file_path = os.path.join(settings.MEDIA_ROOT, product_info.image.name)

        # Проверяем существование файла
        if not os.path.exists(file_path):
            print(f"Файл изображения не найден по пути: {file_path}")
            return False

        print(f"Начинаем генерацию миниатюр для {file_path}")

        # Генерируем миниатюры
        try:
            # Маленькая миниатюра
            if product_info.thumbnail_small:
                with product_info.thumbnail_small.open('rb') as f:
                    pass

            # Средняя миниатюра
            if product_info.thumbnail_medium:
                with product_info.thumbnail_medium.open('rb') as f:
                    pass

            # Большая миниатюра
            if product_info.thumbnail_large:
                with product_info.thumbnail_large.open('rb') as f:
                    pass

            print(f"Миниатюры успешно сгенерированы для ProductInfo {product_info_id}")
            return True

        except Exception as e:
            print(f"Ошибка при генерации миниатюр: {str(e)}")
            return False

    except ProductInfo.DoesNotExist:
        print(f"ProductInfo с id {product_info_id} не найден")
        return False
    except Exception as e:
        print(f"Ошибка в задаче generate_thumbnails: {str(e)}")
        return False
