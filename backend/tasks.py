from celery import shared_task
from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.utils.html import strip_tags
from django.conf import settings
from django.db import transaction
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
def reset_password_request_token(task_id):
    print('запуск задачи celery1')
    user = User.objects.get(id=task_id)
    print(f"user {user}")
    token, _ = ConfirmEmailToken.objects.get_or_create(user=user)
    email = user.email

    subject = 'Запрос на сброс пароля'
    html_message = render_to_string('password_reset_email.html', {
        'user': user,
        'token': token.key,
    })
    plain_message = strip_tags(html_message)

    send_mail(
        subject,
        plain_message,
        settings.EMAIL_HOST_USER,
        [email],
        fail_silently=False,
        html_message=html_message,
    )

    print("Письмо с токеном сброса пароля отправлено на адрес {}".format(email))


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
