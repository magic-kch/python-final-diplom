from django.contrib.auth import authenticate
from django.contrib.auth.password_validation import validate_password
from django.core.validators import URLValidator
from django.http import JsonResponse
from django.shortcuts import render
from rest_framework.authtoken.models import Token
from rest_framework.exceptions import ValidationError
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView
from yaml import load as load_yaml, Loader
from requests import get


from backend.models import Shop, Product, Category, Parameter, ProductParameter, OrderItem, Order, Contact, \
    ConfirmEmailToken

from backend.serializers import UserSerializer, CategorySerializer, ShopSerializer, ProductInfoSerializer, \
    OrderItemSerializer


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
    - post: Update the account details of the authenticated user.

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
                Update the account details of the authenticated user.

                Args:
                - request (Request): The Django request object.

                Returns:
                - JsonResponse: The response indicating the status of the operation and any errors.
                """
        if not request.user.is_authenticated:
            return JsonResponse({'Status': False, 'Error': 'Log in required'}, status=403)
        # проверяем обязательные аргументы

        if 'password' in request.data:
            errors = {}
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
                request.user.set_password(request.data['password'])

        # проверяем остальные данные
        user_serializer = UserSerializer(request.user, data=request.data, partial=True)
        if user_serializer.is_valid():
            user_serializer.save()
            return JsonResponse({'Status': True})
        else:
            return JsonResponse({'Status': False, 'Errors': user_serializer.errors})


class LoginAccount(APIView):
    """
    Класс для авторизации пользователей
    """

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


class PartnerUpdate(APIView):
    """
    Класс для обновления прайса от поставщика
    """
    def post(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return JsonResponse({'Status': False, 'Error': 'Log in required'}, status=403)

        # if request.user.type != 'shop':
        #     return JsonResponse({'Status': False, 'Error': 'Только для магазинов'}, status=403)

        url = request.data.get('url')
        if url:
            validate_url = URLValidator()
            try:
                validate_url(url)
            except ValidationError as e:
                return JsonResponse({'Status': False, 'Error': str(e)})
            else:
                stream = get(url).content

                data = load_yaml(stream, Loader=Loader)

                shop, _ = Shop.objects.get_or_create(name=data['shop'], user_id=request.user.id)

                for category in data['categories']:
                    category_object, _ = Category.objects.get_or_create(id=category['id'], name=category['name'])
                    category_object.shops.add(shop.id)
                    category_object.save()
                """
                Удаление остатков из базы
                """
                Product.objects.filter(shop_id=shop.id).delete()

                for item in data['goods']:
                    product, _ = Product.objects.get_or_create(name=item['name'], category_id=item['category'])

                    product_info = Product.objects.create(product_id=product.id,
                                                          external_id=item['id'],
                                                          model=item['model'],
                                                          price=item['price'],
                                                          price_rrc=item['price_rrc'],
                                                          quantity=item['quantity'],
                                                          shop_id=shop.id)
                    for name, value in item['parameters'].items():
                        parameter_object, _ = Parameter.objects.get_or_create(name=name)
                        product_info.product_parameters.create(parameter_info_id=product_info.id,
                                                               parameter_id=parameter_object.id,
                                                               value=value)

                return JsonResponse({'Status': True})

        return JsonResponse({'Status': False, 'Errors': 'Not enough arguments'})


