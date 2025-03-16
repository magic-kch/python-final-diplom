import os
import pytest
from django import setup

@pytest.fixture(scope='session', autouse=True)
def setup_django():
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'orders.settings')
    setup()
