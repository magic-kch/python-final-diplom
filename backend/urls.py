from django.urls import path
# from django_rest_passwordreset.views import reset_password_request_token, reset_password_confirm

from backend.views import PartnerUpdate

app_name = 'backend'

urlpatterns = [
                path('partner/update', PartnerUpdate.as_view(), name='partner-update'),
                # path('password_reset/', reset_password_request_token, name='password_reset'),
                # path('password_reset/confirm/', reset_password_confirm, name='password_reset_confirm'),
    ]