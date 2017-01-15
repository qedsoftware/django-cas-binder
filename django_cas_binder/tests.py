import httmock
from httmock import HTTMock
from django.test import TestCase, override_settings
from django.conf import settings
from django.contrib.auth import get_user_model

from django_cas_binder.models import CASUser
from django_cas_binder.auth_backends import CASBinderBackend


class FakeCAS(object):
    body = (
        '<cas:serviceResponse xmlns:cas="http://www.yale.edu/tp/cas">'
         + '<cas:authenticationSuccess>'
             + '<cas:user>fake_universal_id</cas:user>'
             + '<cas:attributes>'
                + '<cas:email>fake_email@qed.ai</cas:email>'
                + '<cas:username>fake_username</cas:username>'
             + '</cas:attributes>'
         + '</cas:authenticationSuccess>'
         + '</cas:serviceResponse>'
    )  # NOQA
    headers = {
        'Content-Type': 'text/xml; charset=utf-8',
        'Date': 'Tue, 10 Jan 2017 20:11:16 GMT',
        'X-Frame-Options': 'SAMEORIGIN',
        'Strict-Transport-Security': 'max-age=31536000;',
        'Cache-Control': 'must-revalidate, no-store, no-cache, max-age=0',
        'Last-Modified': 'Tue, 10 Jan 2017 20:11:16 GMT',
        'Server': 'nginx/1.10.1',
        'Connection': 'keep-alive',
        'Expires': 'Tue, 10 Jan 2017 20:11:16 GMT',
        'Transfer-Encoding': 'chunked',
    }

    @httmock.all_requests
    def get(self, url, request):
        self.last_request = request.original
        return httmock.response(200, self.body, self.headers)


@override_settings(CAS_SERVER_URL='http://fake-cas.qed.ai/')
class TestCASBinderBackend__UserExists(TestCase):
    def setUp(self):
        class FakeRequest(object):
            def __init__(self):
                self.session = {}

        self.ticket = 'fake_ticket'
        self.service = 'http://fake-service.qed.ai'
        self.django_request = FakeRequest()
        self.fake_cas = FakeCAS()
        self.user = get_user_model().objects.create_user(
            username='fake_username', password='')
        self.cas_user = CASUser.objects.create(
            user=self.user, universal_id='fake_universal_id')

    def perform_auth(self):
        with HTTMock(self.fake_cas.get):
            return CASBinderBackend().authenticate(
                self.ticket, self.service, self.django_request
            )

    def test_auth_backend_should_supply_correct_request_to_cas(self):
        self.perform_auth()

        self.assertEqual(
            self.fake_cas.last_request.params['ticket'], self.ticket)
        self.assertEqual(
            self.fake_cas.last_request.params['service'], self.service)
        self.assertEqual(
            self.fake_cas.last_request.url,
            settings.CAS_SERVER_URL + 'serviceValidate',
        )

    def test_auth_backend_should_return_correct_user_instance(self):
        authenticated_user = self.perform_auth()

        self.assertEqual(self.user.pk, authenticated_user.pk)

    def test_auth_backend_should_set_request_session_attributes(self):
        self.perform_auth()

        self.assertEqual(
            self.django_request.session['attributes']['username'],
            'fake_username',
        )
        self.assertEqual(
            self.django_request.session['attributes']['email'],
            'fake_email@qed.ai',
        )


@override_settings(CAS_SERVER_URL='http://fake-cas.qed.ai/')
class TestCASBinderBackend__UserDoesNotExist(TestCase):
    def setUp(self):
        class FakeRequest(object):
            def __init__(self):
                self.session = {}

        self.ticket = 'fake_ticket'
        self.service = 'http://fake-service.qed.ai'
        self.django_request = FakeRequest()
        self.fake_cas = FakeCAS()

    def perform_auth(self):
        with HTTMock(self.fake_cas.get):
            return CASBinderBackend().authenticate(
                self.ticket, self.service, self.django_request
            )

    @override_settings(CAS_CREATE_USER=True)
    def test_user_and_cas_user_should_be_created_when_creation_turned_on(self):
        self.assertEqual(list(get_user_model().objects.all()), [])
        self.assertEqual(list(CASUser.objects.all()), [])
        self.perform_auth()
        (user,) = list(get_user_model().objects.all())
        (cas_user,) = list(CASUser.objects.all())
        self.assertEqual(user.username, 'fake_username')
        self.assertEqual(user.email, 'fake_email@qed.ai')
        self.assertEqual(cas_user.user.pk, user.pk)
        self.assertEqual(cas_user.universal_id, 'fake_universal_id')

    @override_settings(CAS_CREATE_USER=False)
    def test_user_and_cas_user_should_be_created_when_creation_turned_off(self):
        self.assertEqual(list(get_user_model().objects.all()), [])
        self.assertEqual(list(CASUser.objects.all()), [])
        res = self.perform_auth()
        self.assertIsNone(res)
        self.assertEqual(list(get_user_model().objects.all()), [])
        self.assertEqual(list(CASUser.objects.all()), [])
