import os
from celery import Celery

# Set the default Django settings module for the 'celery' program.
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'orders.settings')

app = Celery('backend')

# Using a string here means the worker doesn't have to serialize
# the configuration object to child processes.
app.config_from_object('django.conf:settings', namespace='CELERY')

# Enable broker connection retry on startup
app.conf.broker_connection_retry_on_startup = True

# Update broker URL for Redis in Docker
app.conf.update(
    broker_url='redis://redis:6379/0',
    result_backend='redis://redis:6379/1',
    accept_content=['json'],
    task_serializer='json',
    result_serializer='json',
    timezone='UTC',
    enable_utc=True,
)

# Load task modules from all registered Django app configs.
app.autodiscover_tasks()

# For backward compatibility
celery = app

@app.task(bind=True)
def debug_task(self):
    print(f'Request: {self.request!r}')
