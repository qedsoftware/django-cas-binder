#!/usr/bin/env python
from subprocess import check_call

check_call("flake8", shell=True)
check_call("./django_tests.py", shell=True)
