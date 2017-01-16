#!/usr/bin/env python
from distutils.core import setup


setup(
    name='django_cas_binder',
    version='1.5',
    description=(
        'A thin wrapper around django-cas-ng that allows to use identifier '
        'other than username.'
    ),
    author='',
    author_email='',
    url='',
    packages=['django_cas_binder', 'django_cas_binder.migrations'],
)
