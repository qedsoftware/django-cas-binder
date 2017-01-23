#!/usr/bin/env python
from distutils.core import setup


setup(
    name='django_cas_binder',
    version='1.5.1',
    description=(
        'A thin wrapper around django-cas-ng that allows to use identifier '
        'other than username.'
    ),
    author='Quantitative Engineering Design Inc.',
    author_email='',
    url='',
    packages=['django_cas_binder', 'django_cas_binder.migrations'],
    classifiers=[
        'Environment :: Web Environment',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: BSD License',
        'Operating System :: OS Independent',
        'Programming Language :: Python :: 2.7',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.2',
        'Programming Language :: Python :: 3.3',
        'Programming Language :: Python :: 3.4',
        'Programming Language :: Python :: 3.5',
        'Framework :: Django',
    ],
    install_requires=[
        "django>=1.9.0"
    ]
)
