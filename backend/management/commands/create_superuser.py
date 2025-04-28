from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model

class Command(BaseCommand):
    help = 'Создает суперпользователя с заданным email и паролем'

    def handle(self, *args, **kwargs):
        User = get_user_model()
        email = 'admin@admin.ru'
        password = 'admin'

        if not User.objects.filter(email=email).exists():
            User.objects.create_superuser(username='admin', email=email, password=password)
            self.stdout.write(self.style.SUCCESS("Суперпользователь создан."))
        else:
            self.stdout.write(self.style.WARNING("Суперпользователь уже существует."))
