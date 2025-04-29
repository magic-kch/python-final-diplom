from celery import shared_task
from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string
from django.utils.html import strip_tags
from django.conf import settings
from django.db import transaction
from django_rest_passwordreset.models import ResetPasswordToken
from requests import get
from yaml import load as load_yaml, Loader

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
