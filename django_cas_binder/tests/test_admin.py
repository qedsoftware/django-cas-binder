import json

import responses
from django.test import TestCase, RequestFactory, override_settings
from django.contrib.auth import get_user_model
from django.contrib.auth.hashers import check_password, is_password_usable
from django.contrib.admin import site as admin_site
from django.contrib.messages.storage.session import SessionStorage
from django.contrib.messages import get_messages
from django.contrib import messages
from django.core.exceptions import SuspiciousOperation

from django_cas_binder.admin import CasAwareUserAdmin
from django_cas_binder.models import CASUser

User = get_user_model()


class TestGetActions(TestCase):
    def test_superuser(self):
        request = RequestFactory().get('/')
        request.user = User(is_superuser=True)
        admin = CasAwareUserAdmin(User, admin_site)

        actions = admin.get_actions(request)
        self.assertIn('export_users', actions)
        self.assertIn('enable_cas_login', actions)

    def test_non_superuser(self):
        request = RequestFactory().get('/')
        request.user = User(is_superuser=False)
        admin = CasAwareUserAdmin(User, admin_site)

        actions = admin.get_actions(request)
        self.assertNotIn('export_users', actions)
        self.assertNotIn('enable_cas_login', actions)


class TestCSVExport(TestCase):
    def test_export_users(self):
        fake_user = User.objects.create_user(
            'fake_user', 'fake_user@fake_domain.com', 'fake_password')
        fake_user.is_superuser = True
        admin = CasAwareUserAdmin(User, admin_site)
        request = RequestFactory().get('/')
        request.user = fake_user
        response = admin.export_users(request, User.objects.all())
        email, username, password_hash = response.content.split(b',')
        password_hash = password_hash.decode('utf-8').strip()
        self.assertEqual(email, b'fake_user@fake_domain.com')
        self.assertEqual(username, b'fake_user')
        self.assertTrue(is_password_usable(password_hash))
        self.assertTrue(check_password('fake_password', password_hash))

    def test_export_users_by_a_non_superuser(self):
        fake_user = User.objects.create_user(
            'fake_user', 'fake_user@fake_domain.com', 'fake_password')
        admin = CasAwareUserAdmin(User, admin_site)
        request = RequestFactory().get('/')
        request.user = fake_user
        with self.assertRaises(SuspiciousOperation):
            admin.export_users(request, User.objects.all())


@override_settings(CAS_SERVER_URL="https://fake-cas.qed.ai/")
class TestEnableCASLogin(TestCase):
    def fake_cas_universal_ids_endpoint(self, request):
        data = json.loads(request.body.decode('utf-8'))
        self.assertEqual(data, {'emails': ['blah@example.com']})
        return (200, {}, json.dumps({
            'universal_ids': {'blah@example.com': 'marchew'}}))

    @responses.activate
    def test_should_add_casuser_if_does_not_exist(self):
        responses.add_callback(
            responses.POST, "https://fake-cas.qed.ai/api/universal_ids/",
            callback=self.fake_cas_universal_ids_endpoint,
            content_type='application/json',
        )
        request = RequestFactory().get('/')
        request.user = User(is_superuser=True)
        user = User.objects.create_user("blah", "blah@example.com")
        queryset = User.objects.all()
        admin = CasAwareUserAdmin(User, admin_site)
        admin.enable_cas_login(request, queryset)

        cas_user = CASUser.objects.get(user=user)
        self.assertEqual(cas_user.universal_id, "marchew")

    @responses.activate
    def test_should_update_casuser_if_exists(self):
        responses.add_callback(
            responses.POST, "https://fake-cas.qed.ai/api/universal_ids/",
            callback=self.fake_cas_universal_ids_endpoint,
            content_type='application/json',
        )
        request = RequestFactory().get('/')
        request.user = User(is_superuser=True)
        user = User.objects.create_user("blah", "blah@example.com")
        cas_user = CASUser.objects.create(user=user, universal_id="placki")
        queryset = User.objects.all()
        admin = CasAwareUserAdmin(User, admin_site)
        admin.enable_cas_login(request, queryset)

        cas_user.refresh_from_db()
        self.assertEqual(cas_user.universal_id, "marchew")

    @responses.activate
    def test_should_show_error_message_if_user_does_not_exist_in_cas(self):
        responses.add(
            responses.POST, "https://fake-cas.qed.ai/api/universal_ids/",
            json={'errors': [dict(
                error_code='no_such_user',
                error_message='User with given email was not found.',
                email='nonexistent@example.com',
            )]}, status=404,
        )
        request = RequestFactory().get('/')
        request.session = {}
        request.user = User(is_superuser=True)
        request._messages = SessionStorage(request)
        User.objects.create_user("blah", "blah@example.com")
        queryset = User.objects.all()
        admin = CasAwareUserAdmin(User, admin_site)
        admin.enable_cas_login(request, queryset)

        msg, = get_messages(request)
        self.assertEqual(
            msg.message,
            'nonexistent@example.com - User with given email was not found.')
        self.assertEqual(msg.level, messages.ERROR)

    @responses.activate
    def test_should_truncate_error_messages_if_there_are_too_many(self):
        responses.add(
            responses.POST, "https://fake-cas.qed.ai/api/universal_ids/",
            json={'errors': [dict(
                error_code='no_such_user',
                error_message='User with given email was not found.',
                email='nonexistent@example.com',
            ) for i in range(0, 100)]}, status=404,
        )
        request = RequestFactory().get('/')
        request.session = {}
        request._messages = SessionStorage(request)
        request.user = User(is_superuser=True)
        User.objects.create_user("blah", "blah@example.com")
        queryset = User.objects.all()
        admin = CasAwareUserAdmin(User, admin_site)
        admin.enable_cas_login(request, queryset)

        msgs = list(get_messages(request))
        self.assertTrue(len(msgs) < 30)
        self.assertEqual(
            msgs[0].message,
            'nonexistent@example.com - User with given email was not found.')
        self.assertEqual(msgs[0].level, messages.ERROR)
        self.assertEqual(
            msgs[-1].message,
            '%d other errors occurred' % (100 - len(msgs) + 1))
        self.assertEqual(msgs[-1].level, messages.ERROR)

    @responses.activate
    def test_should_handle_unknown_errors(self):
        responses.add(
            responses.POST, "https://fake-cas.qed.ai/api/universal_ids/",
            json={'errors': [dict(
                error_code='fake_unknown_error',
                error_message='Fake unknown error.',
            )]}, status=606,
        )
        request = RequestFactory().get('/')
        request.session = {}
        request._messages = SessionStorage(request)
        request.user = User(is_superuser=True)
        User.objects.create_user("blah", "blah@example.com")
        queryset = User.objects.all()
        admin = CasAwareUserAdmin(User, admin_site)
        admin.enable_cas_login(request, queryset)

        msg, = get_messages(request)
        self.assertEqual(
            msg.message,
            'Fake unknown error.')
        self.assertEqual(msg.level, messages.ERROR)

    def test_should_reject_non_superuser(self):
        request = RequestFactory().get('/')
        request.user = User()
        admin = CasAwareUserAdmin(User, admin_site)
        queryset = User.objects.all()
        with self.assertRaises(SuspiciousOperation):
            admin.enable_cas_login(request, queryset)
