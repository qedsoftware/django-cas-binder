#!/usr/bin/env python

from django.test.runner import DiscoverRunner
from django_cas_binder.setup_django import setup_django


def main():
    setup_django()

    test_runner = DiscoverRunner(verbosity=1)
    test_runner.run_tests(['django_cas_binder'])


if __name__ == '__main__':
    main()
