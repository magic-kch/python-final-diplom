from distutils.util import strtobool
from celery.result import AsyncResult

from django.contrib.auth import authenticate
from django.contrib.auth.password_validation import validate_password
from django.core.validators import URLValidator
from django.http import JsonResponse
from django.db import IntegrityError
from django.db.models import Q, Sum, F

from rest_framework import status
from rest_framework.authtoken.models import Token
from rest_framework.exceptions import ValidationError
from rest_framework.generics import ListAPIView
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from ujson import loads as load_json

from backend.tasks import reset_password_request_token, update_partner_price
from backend.models import Shop, Product, Category, Parameter, User, OrderItem, Order, Contact, \
    ConfirmEmailToken, ProductInfo
from backend.serializers import UserSerializer, CategorySerializer, ShopSerializer, ProductInfoSerializer, \
    OrderItemSerializer, OrderSerializer, ContactSerializer, PasswordResetSerializer
from backend.signals import new_order

from django.core.cache import cache
from cachalot.api import invalidate
from datetime import datetime
import os

class PasswordResetView(APIView):
    def post(self, request):
        serializer = PasswordResetSerializer(data=request.data)
        if serializer.is_valid():
            email = serializer.validated_data['email']
            user = User.objects.get(email=email)
            user_id = user.id
            print('запуск задачи celery')
            reset_password_request_token.delay(user_id)  # вызываем задачу в фоновом режиме
            return Response({'message': 'Письмо с инструкциями по сбросу пароля отправлено на ваш email'}, status=200)
        else:
            return Response(serializer.errors, status=400)


class RegisterAccount(APIView):
    """
    Для регистрации покупателей
    """

    # Регистрация методом POST

    def post(self, request, *args, **kwargs):
        """
            Process a POST request and create a new user.

            Args:
                request (Request): The Django request object.

            Returns:
                JsonResponse: The response indicating the status of the operation and any errors.
            """
        # проверяем обязательные аргументы
        if {'first_name', 'last_name', 'email', 'password', 'company', 'position'}.issubset(request.data):

            # проверяем пароль на сложность
            try:
                validate_password(request.data['password'])
            except Exception as password_error:
                error_array = []
                # noinspection PyTypeChecker
                for item in password_error:
                    error_array.append(item)
                return JsonResponse({'Status': False, 'Errors': {'password': error_array}})
            else:
                # проверяем данные для уникальности имени пользователя

                user_serializer = UserSerializer(data=request.data)
                if user_serializer.is_valid():
                    # сохраняем пользователя
                    user = user_serializer.save()
                    user.set_password(request.data['password'])
                    user.save()
                    return JsonResponse({'Status': True})
                else:
                    return JsonResponse({'Status': False, 'Errors': user_serializer.errors})

        return JsonResponse({'Status': False, 'Errors': 'Not enough arguments'})


class ConfirmAccount(APIView):
    """
    Класс для подтверждения почтового адреса
    """

    # Регистрация методом POST
    def post(self, request, *args, **kwargs):
        """
                Подтверждает почтовый адрес пользователя.

                Args:
                - request (Request): The Django request object.

                Returns:
                - JsonResponse: The response indicating the status of the operation and any errors.
                """
        # проверяем обязательные аргументы
        if {'email', 'token'}.issubset(request.data):

            token = ConfirmEmailToken.objects.filter(user__email=request.data['email'],
                                                     key=request.data['token']).first()
            if token:
                token.user.is_active = True
                token.user.save()
                token.delete()
                return JsonResponse({'Status': True})
            else:
                return JsonResponse({'Status': False, 'Errors': 'Неправильно указан токен или email'})

        return JsonResponse({'Status': False, 'Errors': 'Не указаны все необходимые аргументы'})


class AccountDetails(APIView):
    """
    A class for managing user account details.

    Methods:
    - get: Retrieve the details of the authenticated user.
    - post: Update the account details of the authenticated user, including avatar.

    Attributes:
    - None
    """

    # получить данные
    def get(self, request: Request, *args, **kwargs):
        """
               Retrieve the details of the authenticated user.

               Args:
               - request (Request): The Django request object.

               Returns:
               - Response: The response containing the details of the authenticated user.
        """
        if not request.user.is_authenticated:
            return JsonResponse({'Status': False, 'Error': 'Log in required'}, status=403)

        serializer = UserSerializer(request.user)
        return Response(serializer.data)

    # Редактирование методом POST
    def post(self, request, *args, **kwargs):
        """
                Update the account details of the authenticated user, including avatar.
                If avatar is provided, it will replace the existing one.
                """
        if not request.user.is_authenticated:
            return JsonResponse({'Status': False, 'Error': 'Log in required'}, status=403)

        # Handle password change if provided
        if 'password' in request.data:
            try:
                validate_password(request.data['password'])
                request.user.set_password(request.data['password'])
                request.user.save()
            except Exception as password_error:
                error_array = []
                for item in password_error:
                    error_array.append(item)
                return JsonResponse({'Status': False, 'Errors': {'password': error_array}})

        # Handle avatar upload if provided
        if 'avatar' in request.FILES:
            avatar = request.FILES['avatar']
            
            # Проверяем размер файла (1MB = 1048576 bytes)
            max_size = 1 * 1024 * 1024
            if avatar.size > max_size:
                return JsonResponse(
                    {'Status': False, 'Error': 'Размер файла не должен превышать 1 МБ'},
                    status=400
                )
            
            # Удаляем старый аватар, если он существует
            if request.user.avatar:
                try:
                    # Получаем путь к файлу
                    old_avatar = request.user.avatar
                    # Сначала сохраняем новый аватар, чтобы не потерять ссылку при ошибке
                    request.user.avatar = avatar
                    request.user.save()
                    # Удаляем старый файл после успешного сохранения нового
                    if os.path.isfile(old_avatar.path):
                        os.remove(old_avatar.path)
                except Exception as e:
                    return JsonResponse(
                        {'Status': False, 'Error': f'Ошибка при замене аватарки: {str(e)}'},
                        status=500
                    )
            else:
                # Если старого аватара не было, просто сохраняем новый
                request.user.avatar = avatar
                request.user.save()
            
            return JsonResponse({
                'Status': True, 
                'Message': 'Аватар успешно обновлен',
                'avatar_url': request.user.avatar.url if request.user.avatar else None
            })

        # Handle other user data
        user_serializer = UserSerializer(request.user, data=request.data, partial=True)
        if user_serializer.is_valid():
            user_serializer.save()
            return JsonResponse({
                'Status': True, 
                'Message': 'Данные успешно обновлены',
                'avatar_url': request.user.avatar.url if request.user.avatar else None
            })
        else:
            return JsonResponse({'Status': False, 'Errors': user_serializer.errors})


class LoginAccount(APIView):
    """
    Класс для авторизации пользователей
    """
    throttle_scope = 'auth'

    # Авторизация методом POST
    def post(self, request, *args, **kwargs):
        """
                Authenticate a user.

                Args:
                    request (Request): The Django request object.

                Returns:
                    JsonResponse: The response indicating the status of the operation and any errors.
                """
        if {'email', 'password'}.issubset(request.data):
            user = authenticate(request, username=request.data['email'], password=request.data['password'])

            if user is not None:
                if user.is_active:
                    token, _ = Token.objects.get_or_create(user=user)

                    return JsonResponse({'Status': True, 'Token': token.key})

            return JsonResponse({'Status': False, 'Errors': 'Log in unsuccessful'})

        return JsonResponse({'Status': False, 'Errors': 'Not enough arguments'})


class CategoryView(ListAPIView):
    """
    Класс для просмотра категорий
    """
    queryset = Category.objects.all()
    serializer_class = CategorySerializer


class ShopView(ListAPIView):
    """
    Класс для просмотра списка магазинов
    """
    queryset = Shop.objects.filter(state=True)
    serializer_class = ShopSerializer


class ProductInfoView(APIView):
    """
        A class for searching products.

        Methods:
        - get: Retrieve the product information based on the specified filters.

        Attributes:
        - None
        """

    def get(self, request: Request, *args, **kwargs):
        """
               Retrieve the product information based on the specified filters.

               Args:
               - request (Request): The Django request object.

               Returns:
               - Response: The response containing the product information.
               """
        query = Q(shop__state=True)
        shop_id = request.query_params.get('shop_id')
        category_id = request.query_params.get('category_id')

        if shop_id:
            query = query & Q(shop_id=shop_id)

        if category_id:
            query = query & Q(product__category_id=category_id)

        # фильтруем и отбрасываем дубликаты
        queryset = ProductInfo.objects.filter(
            query).select_related(
            'shop', 'product__category').prefetch_related(
            'product_params', 'product_params__parameter').distinct()

        serializer = ProductInfoSerializer(queryset, many=True, context={'request': request})

        return Response(serializer.data)


class ProductInfoImageView(APIView):
    """
    Класс для обновления изображений товаров
    """

    def patch(self, request, pk, *args, **kwargs):
        """
        Обновление изображения товара

        Аргументы:
            request: Объект запроса, содержащий файл изображения
            pk: ID товара (ProductInfo)

        Возвращает:
            Response: Ответ с обновленной информацией о товаре или сообщением об ошибке
        """
        try:
            # Получаем товар по ID
            product_info = ProductInfo.objects.get(id=pk)
        except ProductInfo.DoesNotExist:
            return Response(
                {'Status': False, 'Error': 'Товар не найден'},
                status=status.HTTP_404_NOT_FOUND
            )

        # Проверяем права доступа
        if not request.user.is_authenticated or request.user.type != 'shop':
            return Response(
                {'Status': False, 'Error': 'Только магазины могут обновлять товары'},
                status=status.HTTP_403_FORBIDDEN
            )

        # Получаем файл изображения из запроса
        image_file = request.FILES.get('image')
        if not image_file:
            return Response(
                {'Status': False, 'Error': 'Не указано изображение'},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            # Обновляем изображение
            product_info.image = image_file
            product_info.save()

            # Возвращаем обновленные данные
            serializer = ProductInfoSerializer(product_info, context={'request': request})
            return Response(serializer.data)

        except Exception as e:
            return Response(
                {'Status': False, 'Error': str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class BasketView(APIView):
    """
    A class for managing the user's shopping basket.

    Methods:
    - get: Retrieve the items in the user's basket.
    - post: Add an item to the user's basket.
    - put: Update the quantity of an item in the user's basket.
    - delete: Remove an item from the user's basket.

    Attributes:
    - throttle_scope: The scope for rate limiting this view
    """
    throttle_scope = 'basket'

    # получить корзину
    def get(self, request, *args, **kwargs):
        """
                Retrieve the items in the user's basket.

                Args:
                - request (Request): The Django request object.

                Returns:
                - Response: The response containing the items in the user's basket.
                """
        if not request.user.is_authenticated:
            return JsonResponse({'Status': False, 'Error': 'Log in required'}, status=403)
        basket = Order.objects.filter(
            user_id=request.user.id, state='basket').prefetch_related(
            'ordered_items__product_info__product__category',
            'ordered_items__product_info__product_params__parameter').annotate(
            total_sum=Sum(F('ordered_items__quantity') * F('ordered_items__product_info__price_rrc'))).distinct()

        serializer = OrderSerializer(basket, many=True)
        return Response(serializer.data)

    # редактировать корзину
    def post(self, request, *args, **kwargs):
        """
           Add an items to the user's basket.
            {
            "items": "[{\"product_info\": 5, \"quantity\": 2}, {\"product_info\": 7, \"quantity\": 3}]"
            }

           Args:
           - request (Request): The Django request object.

           Returns:
           - JsonResponse: The response indicating the status of the operation and any errors.
       """
        if not request.user.is_authenticated:
            return JsonResponse({'Status': False, 'Error': 'Log in required'}, status=403)

        items_sting = request.data.get('items')
        if items_sting:
            try:
                items_dict = load_json(items_sting)
            except ValueError:
                return JsonResponse({'Status': False, 'Errors': 'Неверный формат запроса'})
            else:
                basket, _ = Order.objects.get_or_create(user_id=request.user.id, state='basket')
                objects_created = 0
                for order_item in items_dict:
                    order_item.update({'order': basket.id})
                    serializer = OrderItemSerializer(data=order_item)
                    if serializer.is_valid():
                        try:
                            serializer.save()
                        except IntegrityError as error:
                            return JsonResponse({'Status': False, 'Errors': str(error)})
                        else:
                            objects_created += 1

                    else:

                        return JsonResponse({'Status': False, 'Errors': serializer.errors})

                return JsonResponse({'Status': True, 'Создано объектов': objects_created})
        return JsonResponse({'Status': False, 'Errors': 'Не указаны все необходимые аргументы'})

    # удалить товары из корзины
    def delete(self, request, *args, **kwargs):
        """
                Remove  items from the user's basket.

                Args:
                - request (Request): The Django request object.

                Returns:
                - JsonResponse: The response indicating the status of the operation and any errors.
                """
        if not request.user.is_authenticated:
            return JsonResponse({'Status': False, 'Error': 'Log in required'}, status=403)

        items_sting = request.data.get('items')
        if items_sting:
            items_list = items_sting.split(',')
            basket, _ = Order.objects.get_or_create(user_id=request.user.id, state='basket')
            query = Q()
            objects_deleted = False
            for order_item_id in items_list:
                if order_item_id.isdigit():
                    query = query | Q(order_id=basket.id, id=order_item_id)
                    objects_deleted = True

            if objects_deleted:
                deleted_count = OrderItem.objects.filter(query).delete()[0]
                return JsonResponse({'Status': True, 'Удалено объектов': deleted_count})
        return JsonResponse({'Status': False, 'Errors': 'Не указаны все необходимые аргументы'})

    # добавить позиции в корзину
    def put(self, request, *args, **kwargs):
        """
           Update the items in the user's basket.
            {
            "items": "[{\"id\": 5, \"quantity\": 2}, {\"id\": 7, \"quantity\": 3}]"
            }

           Args:
           - request (Request): The Django request object.

           Returns:
           - JsonResponse: The response indicating the status of the operation and any errors.
       """
        if not request.user.is_authenticated:
            return JsonResponse({'Status': False, 'Error': 'Log in required'}, status=403)

        items_sting = request.data.get('items')
        if items_sting:
            try:
                items_dict = load_json(items_sting)
            except ValueError:
                return JsonResponse({'Status': False, 'Errors': 'Неверный формат запроса'})
            else:
                basket, _ = Order.objects.get_or_create(user_id=request.user.id, state='basket')
                objects_updated = 0
                for order_item in items_dict:
                    if type(order_item['id']) == int and type(order_item['quantity']) == int:
                        objects_updated += OrderItem.objects.filter(order_id=basket.id, id=order_item['id']).update(
                            quantity=order_item['quantity'])

                return JsonResponse({'Status': True, 'Обновлено объектов': objects_updated})
        return JsonResponse({'Status': False, 'Errors': 'Не указаны все необходимые аргументы'})


class PartnerUpdate(APIView):
    """
    Асинхронное обновление прайса от поставщика
    """

    def post(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return Response(
                {'Status': False, 'Error': 'Log in required'},
                status=status.HTTP_403_FORBIDDEN
            )

        if request.user.type != 'shop' and not request.user.is_staff:
            return Response(
                {'Status': False, 'Error': 'Только для магазинов и администраторов'},
                status=status.HTTP_403_FORBIDDEN
            )

        # Для администраторов получаем shop_id из запроса
        if request.user.is_staff:
            shop_id = request.data.get('shop_id')
            if not shop_id:
                return Response(
                    {'Status': False, 'Error': 'Для администраторов укажите shop_id'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            try:
                shop = Shop.objects.get(id=shop_id)
            except Shop.DoesNotExist:
                return Response(
                    {'Status': False, 'Error': 'Магазин не найден'},
                    status=status.HTTP_404_NOT_FOUND
                )
        else:
            # Для обычных магазинов используем привязанный магазин
            shop, _ = Shop.objects.get_or_create(user=request.user)

        url = request.data.get('url')
        if url:
            try:
                URLValidator()(url)
            except ValidationError as e:
                return Response(
                    {'Status': False, 'Error': str(e)},
                    status=status.HTTP_400_BAD_REQUEST
                )

            # Запуск асинхронной задачи с передачей shop_id
            task = update_partner_price.delay(
                shop_id=shop.id,
                url=url
            )

            return Response({
                'Status': True,
                'TaskID': task.id,
                'Message': 'Обновление прайса запущено'
            }, status=status.HTTP_202_ACCEPTED)

        return Response(
            {'Status': False, 'Errors': 'Не указан URL'},
            status=status.HTTP_400_BAD_REQUEST
        )


class PartnerState(APIView):
    """
       A class for managing partner state.

       Methods:
       - get: Retrieve the state of the partner.

       Attributes:
       - None
       """
    # получить текущий статус
    def get(self, request, *args, **kwargs):
        """
               Retrieve the state of the partner.

               Args:
               - request (Request): The Django request object.

               Returns:
               - Response: The response containing the state of the partner.
               """
        if not request.user.is_authenticated:
            return JsonResponse({'Status': False, 'Error': 'Log in required'}, status=403)

        if request.user.type != 'shop':
            return JsonResponse({'Status': False, 'Error': 'Только для магазинов'}, status=403)

        shop = request.user.shop
        serializer = ShopSerializer(shop)
        return Response(serializer.data)

    # изменить текущий статус
    def post(self, request, *args, **kwargs):
        """
               Update the state of a partner.

               Args:
               - request (Request): The Django request object.

               Returns:
               - JsonResponse: The response indicating the status of the operation and any errors.
               """
        if not request.user.is_authenticated:
            return JsonResponse({'Status': False, 'Error': 'Log in required'}, status=403)

        if request.user.type != 'shop':
            return JsonResponse({'Status': False, 'Error': 'Только для магазинов'}, status=403)
        state = request.data.get('state')
        if state:
            try:
                Shop.objects.filter(user_id=request.user.id).update(state=strtobool(state))
                return JsonResponse({'Status': True})
            except ValueError as error:
                return JsonResponse({'Status': False, 'Errors': str(error)})

        return JsonResponse({'Status': False, 'Errors': 'Не указаны все необходимые аргументы'})


class PartnerOrders(APIView):
    """
    Класс для получения заказов поставщиками
     Methods:
    - get: Retrieve the orders associated with the authenticated partner.

    Attributes:
    - None
    """

    def get(self, request, *args, **kwargs):
        """
               Retrieve the orders associated with the authenticated partner.

               Args:
               - request (Request): The Django request object.

               Returns:
               - Response: The response containing the orders associated with the partner.
               """
        if not request.user.is_authenticated:
            return JsonResponse({'Status': False, 'Error': 'Log in required'}, status=403)

        if request.user.type != 'shop':
            return JsonResponse({'Status': False, 'Error': 'Только для магазинов'}, status=403)

        order = Order.objects.filter(
            ordered_items__product_info__shop__user_id=request.user.id).exclude(state='basket').prefetch_related(
            'ordered_items__product_info__product__category',
            'ordered_items__product_info__product_params__parameter').select_related('contact').annotate(
            total_sum=Sum(F('ordered_items__quantity') * F('ordered_items__product_info__price'))).distinct()

        serializer = OrderSerializer(order, many=True)
        return Response(serializer.data)


class ContactView(APIView):
    """
       A class for managing contact information.

       Methods:
       - get: Retrieve the contact information of the authenticated user.
       - post: Create a new contact for the authenticated user.
       - put: Update the contact information of the authenticated user.
       - delete: Delete the contact of the authenticated user.

       Attributes:
       - None
       """

    # получить мои контакты
    def get(self, request, *args, **kwargs):
        """
           Retrieve the contact information of the authenticated user.

           Args:
           - request (Request): The Django request object.

           Returns:
           - Response: The response containing the contact information.
       """
        if not request.user.is_authenticated:
            return JsonResponse({'Status': False, 'Error': 'Log in required'}, status=403)
        contact = Contact.objects.filter(
            user_id=request.user.id)
        serializer = ContactSerializer(contact, many=True)
        return Response(serializer.data)

    # добавить новый контакт
    def post(self, request, *args, **kwargs):
        """
           Create a new contact for the authenticated user.

           Args:
           - request (Request): The Django request object.

           Returns:
           - JsonResponse: The response indicating the status of the operation and any errors.
       """
        if not request.user.is_authenticated:
            return JsonResponse({'Status': False, 'Error': 'Log in required'}, status=403)

        if {'city', 'street', 'phone'}.issubset(request.data):
            data = request.data.copy()
            data.update({'user': request.user.id})
            serializer = ContactSerializer(data=data)

            if serializer.is_valid():
                serializer.save()
                return JsonResponse({'Status': True})
            else:
                return JsonResponse({'Status': False, 'Errors': serializer.errors})

        return JsonResponse({'Status': False, 'Errors': 'Не указаны все необходимые аргументы'})

    # удалить контакт
    def delete(self, request, *args, **kwargs):
        """
           Delete the contact of the authenticated user.

           Args:
           - request (Request): The Django request object.

           Returns:
           - JsonResponse: The response indicating the status of the operation and any errors.
       """
        if not request.user.is_authenticated:
            return JsonResponse({'Status': False, 'Error': 'Log in required'}, status=403)

        items_sting = request.data.get('items')
        if items_sting:
            items_list = items_sting.split(',')
            query = Q()
            objects_deleted = False
            for contact_id in items_list:
                if contact_id.isdigit():
                    query = query | Q(user_id=request.user.id, id=contact_id)
                    objects_deleted = True

            if objects_deleted:
                deleted_count = Contact.objects.filter(query).delete()[0]
                return JsonResponse({'Status': True, 'Удалено объектов': deleted_count})
        return JsonResponse({'Status': False, 'Errors': 'Не указаны все необходимые аргументы'})

    # редактировать контакт
    def put(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            """
               Update the contact information of the authenticated user.

               Args:
               - request (Request): The Django request object.

               Returns:
               - JsonResponse: The response indicating the status of the operation and any errors.
            """
            return JsonResponse({'Status': False, 'Error': 'Log in required'}, status=403)

        if 'id' in request.data:
            if request.data['id'].isdigit():
                contact = Contact.objects.filter(id=request.data['id'], user_id=request.user.id).first()
                print(contact)
                if contact:
                    serializer = ContactSerializer(contact, data=request.data, partial=True)
                    if serializer.is_valid():
                        serializer.save()
                        return JsonResponse({'Status': True})
                    else:
                        return JsonResponse({'Status': False, 'Errors': serializer.errors})

        return JsonResponse({'Status': False, 'Errors': 'Не указаны все необходимые аргументы'})


class OrderView(APIView):
    """
    Класс для получения и размещения заказов пользователями
    Methods:
    - get: Retrieve the details of a specific order.
    - post: Create a new order.
    - put: Update the details of a specific order.
    - delete: Delete a specific order.

    Attributes:
    - None
    """

    # получить мои заказы
    def get(self, request, *args, **kwargs):
        """
               Retrieve the details of user orders.

               Args:
               - request (Request): The Django request object.

               Returns:
               - Response: The response containing the details of the order.
               """
        if not request.user.is_authenticated:
            return JsonResponse({'Status': False, 'Error': 'Log in required'}, status=403)
        order = Order.objects.filter(
            user_id=request.user.id).exclude(state='basket').prefetch_related(
            'ordered_items__product_info__product__category',
            'ordered_items__product_info__product_params__parameter').select_related('contact').annotate(
            total_sum=Sum(F('ordered_items__quantity') * F('ordered_items__product_info__price'))).distinct()

        serializer = OrderSerializer(order, many=True)
        return Response(serializer.data)

    # разместить заказ из корзины
    def post(self, request, *args, **kwargs):
        """
               Put an order and send a notification.

               Args:
               - request (Request): The Django request object.

               Returns:
               - JsonResponse: The response indicating the status of the operation and any errors.
               """
        if not request.user.is_authenticated:
            return JsonResponse({'Status': False, 'Error': 'Log in required'}, status=403)

        if {'id', 'contact'}.issubset(request.data):
            if request.data['id'].isdigit():
                try:
                    print(f"user_id {request.user.id}")
                    print(Order.objects.get(id=request.data['id']))
                    is_updated = Order.objects.filter(
                        user_id=request.user.id, id=request.data['id']).update(
                        contact_id=request.data['contact'],
                        state='new')
                except IntegrityError as error:
                    print(error)
                    return JsonResponse({'Status': False, 'Errors': 'Неправильно указаны аргументы'})
                else:
                    if is_updated:
                        new_order.send(sender=self.__class__, user_id=request.user.id)
                        return JsonResponse({'Status': True})

        return JsonResponse({'Status': False, 'Errors': 'Не указаны все необходимые аргументы'})


class TaskStatus(APIView):
    """
    Проверка статуса Celery задачи
    """

    def get(self, request, *args, **kwargs):
        task_id = request.query_params.get('task_id')

        if not task_id:
            return Response(
                {'error': 'Не указан task_id'},
                status=status.HTTP_400_BAD_REQUEST
            )

        task_result = AsyncResult(task_id)

        response_data = {
            'task_id': task_id,
            'status': task_result.status,
            'result': task_result.result
        }

        if task_result.failed():
            response_data['error'] = str(task_result.result)
            response_data['traceback'] = task_result.traceback

        return Response(response_data, status=status.HTTP_200_OK)


class CachedDataView(APIView):
    def get(self, request):
        # Пример кеширования данных
        key = 'cached_data'
        
        # Попытка получить данные из кэша
        data = cache.get(key)
        
        if data is None:
            # Если данных нет в кэше, создаем новые
            data = {
                'timestamp': datetime.now().isoformat(),
                'data': 'Some cached data'
            }
            
            # Кэшируем данные на 10 минут
            cache.set(key, data, timeout=60*10)
            
        return JsonResponse(data)


# Пример использования кэширования с помощью cachalot
class ProductListView(APIView):
    def get(self, request):
        # При первом запросе данные будут получены из базы
        # При последующих запросах данные будут взяты из кэша
        products = Product.objects.all()
        
        if not products.exists():
            return JsonResponse({
                'status': 'success',
                'message': 'No products found',
                'products': []
            })
        
        return JsonResponse({
            'status': 'success',
            'products': list(products.values())
        })


# Пример обновления кэша при изменении данных
class ProductUpdateView(APIView):
    def post(self, request, product_id):
        try:
            # Обновляем данные в базе
            product = Product.objects.get(id=product_id)
            # Здесь должен быть код для обновления продукта
            
            # Инвалидируем кэш для таблицы Product
            invalidate(Product)
            
            return JsonResponse({
                'status': 'success',
                'message': f'Product {product_id} updated successfully'
            })
            
        except Product.DoesNotExist:
            return JsonResponse({
                'status': 'error',
                'message': f'Product with id {product_id} not found'
            }, status=404)
        except Exception as e:
            return JsonResponse({
                'status': 'error',
                'message': str(e)
            }, status=500)
