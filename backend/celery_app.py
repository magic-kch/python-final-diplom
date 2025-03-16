# from celery import Celery
# import os
#
# os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'orders.settings')
# app = Celery('backend')
#
# app.config_from_object('django.conf:settings', namespace='CELERY')
#
# app.conf.broker_connection_retry_on_startup = True
# # Load task modules from all registered Django app configs.
# app.autodiscover_tasks()
# Standard library imports
import os

# Celery
from celery import Celery

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'orders.settings')

app = Celery('backend')

app.config_from_object('django.conf:settings', namespace='CELERY')
app.conf.broker_connection_retry_on_startup = True
app.conf.update(
    broker_url=os.getenv('REDIS_URL', 'redis://localhost:6379/0'),
)

app.autodiscover_tasks()
celery = app

@app.task(bind=True)
def debug_task(self):
    print('Request: {0!r}'.format(self.request))
