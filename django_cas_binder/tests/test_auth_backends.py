from django.test import TestCase

from django_cas_binder.auth_backends import CASBinderBackend


class TestCasBackends(TestCase):
    def test_user_can_authenticate(self):
        backends = CASBinderBackend()
        self.assertTrue(backends.user_can_authenticate(object()))
