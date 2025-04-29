# python-final-diplom_REST API basics - CRUD
## base_url = http://localhost/api/v1/
### Контакт

- **GET** `{{base_url}}/contact`
- **POST** `{{base_url}}/contact`
- **PUT** `{{base_url}}/contact`
- **DELETE** `{{base_url}}/contact`

### Корзина

- **GET** `{{base_url}}/basket`
- **POST** `{{base_url}}/basket`
- **PUT** `{{base_url}}/basket`
- **DELETE** `{{base_url}}/basket`

### Пользователь

- **GET** `{{base_url}}/user`
- **POST** `{{base_url}}/user/register`
- **POST** `{{base_url}}/user/login`
- **POST** `{{base_url}}/user/password_reset`

### Партнер

- **GET** `{{base_url}}/partner/state`
- **POST** `{{base_url}}/partner/state`
- **GET** `{{base_url}}/partner/orders`

### Заказ

- **GET** `{{base_url}}/order`
- **POST** `{{base_url}}/order`

### Информация о продукте

- **GET** `{{base_url}}/product_info?shop_id=1&category_id=1`