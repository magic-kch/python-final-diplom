from celery import shared_task
from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.utils.html import strip_tags
from django.conf import settings

from backend.models import User, ConfirmEmailToken


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
