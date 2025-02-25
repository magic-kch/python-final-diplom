from django.contrib import admin
from .models import User, Shop, Category, Product, ProductInfo, Parameter, ProductParameter, Order, OrderItem, \
    Contact, ConfirmEmailToken


@admin.register(User)
class UserAdmin(admin.ModelAdmin):
    list_display = ['email', 'username', 'is_staff', 'is_active', 'is_superuser',]
    list_filter = ['is_staff', 'is_active', 'is_superuser',]
    search_fields = ['email', 'username',]
    search_help_text = 'Введите email или имя пользователя для поиска'


@admin.register(Shop)
class ShopAdmin(admin.ModelAdmin):
    list_display = ['name', 'url', 'user', 'state',]
    list_filter = ['state',]
    search_fields = ['name', 'user']
    search_help_text = 'Введите название магазина или пользователя для поиска'


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ['name', 'get_shops',]
    search_fields = ['name',]
    search_help_text = 'Введите название категории для поиска'

    def get_shops(self, obj):
        return ', '.join([shop.name for shop in obj.shops.all()])

    get_shops.short_description = 'Магазины'


class ProductInfoInline(admin.TabularInline):
    model = ProductInfo
    extra = 0


class ProductParameterInline(admin.TabularInline):
    model = ProductParameter
    extra = 0


@admin.register(ProductInfo)
class ProductInfoAdmin(admin.ModelAdmin):
    inlines = [ProductParameterInline,]
    list_display = ['product', 'external_id', 'shop', 'quantity', 'price', 'price_rrc']
    search_fields = ['product', 'external_id', 'shop']
    search_help_text = 'Введите название продукта или внешний ID для поиска'
    list_filter = ['shop',]


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    inlines = [ProductInfoInline,]
    list_display = ['name', 'category',]
    search_fields = ['name', 'category',]
    search_help_text = 'Введите название продукта или категорию для поиска'
    list_filter = ['category',]


@admin.register(Parameter)
class ParameterAdmin(admin.ModelAdmin):
    list_display = ['name',]
    search_fields = ['name',]
    search_help_text = 'Введите название параметра для поиска'

class OrderItemInline(admin.TabularInline):
    model = OrderItem
    extra = 0
    readonly_fields = ('get_price',)

    def get_price(self, obj):
        return obj.product_info.price_rrc

    get_price.short_description = 'Цена'

@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    inlines = [OrderItemInline,]
    list_display = ['id', 'user', 'dt', 'state', 'contact', 'get_quantity', 'get_total_price']
    list_filter = ['state',]
    search_fields = ['user',]
    search_help_text = 'Введите имя пользователя для поиска'

    def get_total_price(self, obj):
        order_items = obj.ordered_items.all()
        price = sum(item.quantity * item.product_info.price_rrc for item in order_items)
        return price

    def get_quantity(self, obj):
        order_items = obj.ordered_items.all()
        quantities = sum(item.quantity for item in order_items)
        return quantities

    get_total_price.short_description = 'Стоимость заказа'
    get_quantity.short_description = 'Количество'


@admin.register(Contact)
class ContactAdmin(admin.ModelAdmin):
    list_display = ['user', 'city', 'street', 'house', 'structure', 'building', 'apartment', 'phone',]
    search_fields = ['user', 'city', 'phone',]
    search_help_text = 'Введите имя пользователя, город или телефон для поиска'
    list_filter = ['city',]


@admin.register(ConfirmEmailToken)
class ConfirmEmailTokenAdmin(admin.ModelAdmin):
    list_display = ['user', 'key', 'created',]
