from django.urls import path, include
from django_rest_passwordreset.views import reset_password_request_token, reset_password_confirm

from backend.views import PartnerUpdate, ConfirmAccount, RegisterAccount, LoginAccount, AccountDetails, CategoryView, \
    ShopView, ProductInfoView, BasketView, ContactView, PartnerState, PartnerOrders, OrderView, PasswordResetView, \
    TaskStatus

from drf_spectacular.views import SpectacularAPIView, SpectacularRedocView, SpectacularSwaggerView

app_name = 'backend'

urlpatterns = [

    path('partner/update', PartnerUpdate.as_view(), name='partner-update'),
    path('partner/state', PartnerState.as_view(), name='partner-state'),
    path('partner/orders', PartnerOrders.as_view(), name='partner-orders'),
    path('user/register', RegisterAccount.as_view(), name='user-register'),
    path('user/register/confirm', ConfirmAccount.as_view(), name='user-register-confirm'),
    path('user/login', LoginAccount.as_view(), name='user-login'),
    path('user', AccountDetails.as_view(), name='user-details'),
    path('user/password_reset', PasswordResetView.as_view(), name='password-reset'),
    path('user/password_reset/confirm', reset_password_confirm, name='password-reset-confirm'),
    path('categories', CategoryView.as_view(), name='categories'),
    path('shops', ShopView.as_view(), name='shops'),
    path('product_info', ProductInfoView.as_view(), name='product-info'),
    path('basket', BasketView.as_view(), name='basket'),
    path('contact', ContactView.as_view(), name='contact'),
    path('order', OrderView.as_view(), name='order'),
    path('task/status', TaskStatus.as_view(), name='task-status'),

]
