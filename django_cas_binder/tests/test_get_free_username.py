from django.test import TestCase

from django_cas_binder.utils import get_free_username


class TestGetFreeUsername(TestCase):
    def test_free(self):
        def is_free(u):
            return True

        self.assertEqual(get_free_username("blah", is_free, 10), "blah")

    def test_free_4_iterations(self):
        def is_free(u):
            return u == 'blah_4'

        self.assertEqual(get_free_username("blah", is_free, 10), "blah_4")

    def test_limit(self):
        def is_free(u):
            return False

        with self.assertRaises(Exception):
            get_free_username("blah", is_free, 10)
