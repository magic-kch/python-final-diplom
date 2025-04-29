from django.db.models.signals import post_save
from django.dispatch import receiver, Signal
from django_rest_passwordreset.signals import reset_password_token_created

from backend.models import User

from .tasks import send_confirmation_email, send_order_email, send_password_reset_email

new_user_registered = Signal()

new_order = Signal()


@receiver(reset_password_token_created)
def password_reset_token_created(sender, instance, reset_password_token, **kwargs):
    send_password_reset_email.delay(
        user_id=reset_password_token.user.id,
        reset_password_token=reset_password_token.key
    )

@receiver(post_save, sender=User)
def new_user_registered_signal(sender, instance, created, **kwargs):
    if created and not instance.is_active:
        send_confirmation_email.delay(instance.id)

@receiver(new_order)
def new_order_signal(user_id, **kwargs):
    send_order_email.delay(user_id)

