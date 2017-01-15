import django
from django.conf import settings


def setup_django():
    settings.configure(
        INSTALLED_APPS=[
            'django.contrib.auth',
            'django.contrib.contenttypes',
            'django_cas_binder'
        ],
        DATABASES={'default': {
            'ENGINE': 'django.db.backends.sqlite3',
            'NAME': ':memory:'
        }}

    )
    django.setup()
