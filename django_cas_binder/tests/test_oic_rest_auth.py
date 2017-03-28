import responses
from django.test import TestCase, override_settings
from rest_framework.test import APIRequestFactory  # NOQA
import rest_framework.views
from django.contrib.auth import get_user_model

from django_cas_binder.models import CASUser

from django_cas_binder.oic_rest_auth import (
    OICAuthentication, OICScopeClaimPermissionClass, CASResponseError
)


class RestFrameworkOicAuthTestMixin(object):
    """This class exists because requests as created with APIRequestFactory
    are different from those that are fed into authentication class
    .authenticate() method. To workaround this issue, we create a fake view
    with the sole purpose of throwing request.user and request.auth to us.
    Configurable by setting self.permission_classes.
    """

    def simulate_authentication_using_fake_view(self, request):
        """Take a request as produced by APIRequestFactory and return a
        tuple of (user, auth) if succeeded. Otherwise return a response with
        error status code.
        """
        class HelperException(Exception):
            pass

        class FakeView(rest_framework.views.APIView):
            authentication_classes = OICAuthentication,
            if getattr(self, 'permission_classes', None):
                permission_classes = self.permission_classes

            def get(self, request):
                e = HelperException()
                e.request = request
                raise e
        try:
            response = FakeView.as_view()(request)
        except HelperException as e:
            return (e.request.user, e.request.auth)
        else:
            return response

    @responses.activate
    def perform_auth(self, auth, status=200, **kwargs):
        """Take response content and status code of cas/userinfo endpoint to be
        mocked. Perform authentication against this mocked endpoint. Return a
        (user, auth) tuple on success and an instance of
        rest_framework.response.Response on failure.
        """
        responses.add(
            responses.GET,
            "https://fake-cas.qed.ai/openid/.well-known/openid-configuration",
            json={
                "issuer": "https://fake-cas.qed.ai/openid",
                "userinfo_endpoint": "https://fake-cas.qed.ai/openid/userinfo",
            },
            status=200,
        )
        responses.add(
            responses.GET,
            "https://fake-cas.qed.ai/openid/userinfo",  # NOQA
            json=auth,
            status=status,
            **kwargs
        )
        request = APIRequestFactory().get(
            '/', {'access_token': 'fake_access_token'}
        )
        return self.simulate_authentication_using_fake_view(request)


@override_settings(CAS_SERVER_URL="https://fake-cas.qed.ai/")
class TestOICAuthentication(TestCase, RestFrameworkOicAuthTestMixin):
    def test_auth_success(self):
        self.user = get_user_model().objects.create_user(
            username='fake_username', email='fake_email@qed.ai')
        self.cas_user = CASUser.objects.create(
            user=self.user, universal_id='fake_universal_id')
        self.auth = {'universal_id': 'fake_universal_id'}

        user, auth = self.perform_auth(self.auth)

        self.assertEqual(user.pk, self.user.pk)
        self.assertEqual(auth, self.auth)

    def test_auth_no_such_user(self):
        self.auth = {'universal_id': 'fake_universal_id'}

        response = self.perform_auth(self.auth)

        self.assertEqual(response.status_code, 403)
        self.assertEqual(response.data, {
            "detail":
                "user not found, login to the site with the "
                "browser and try again"
        })

    def test_auth_no_universal_id(self):
        self.auth = {"bla": "bla"}
        with self.assertRaises(CASResponseError):
            self.perform_auth(self.auth)

    def test_auth_cas_userinfo_response_401(self):
        self.auth = {"bla": "bla"}

        response = self.perform_auth(
            self.auth, status=401,
            adding_headers={"WWW-Authenticate": "fake_error"}
        )

        self.assertEqual(response.status_code, 403)
        self.assertEqual(response.data, {"detail": "fake_error"})

    def test_auth_cas_userinfo_response_403(self):
        self.auth = {'bla': "bla"}

        response = self.perform_auth(
            self.auth, status=403,
            adding_headers={"WWW-Authenticate": "fake_error"}
        )

        self.assertEqual(response.status_code, 403)
        self.assertEqual(response.data, {"detail": "fake_error"})

    def test_auth_cas_userinfo_response_500(self):
        self.auth = {'bla': 'bla'}

        with self.assertRaises(CASResponseError):
            self.perform_auth(self.auth, status=500)


@override_settings(CAS_SERVER_URL="https://fake-cas.qed.ai/")
class TestOICScopeClaimPermission(TestCase, RestFrameworkOicAuthTestMixin):
    permission_classes = OICScopeClaimPermissionClass("can_blah"),

    def test_auth_success(self):
        self.user = get_user_model().objects.create_user(
            username='fake_username', email='fake_email@qed.ai')
        self.cas_user = CASUser.objects.create(
            user=self.user, universal_id='fake_universal_id')
        self.auth = {'universal_id': 'fake_universal_id', 'can_blah': True}

        user, auth = self.perform_auth(self.auth)

        self.assertEqual(user.pk, self.user.pk)
        self.assertEqual(auth, self.auth)

    def test_auth_permission_not_present(self):
        self.user = get_user_model().objects.create_user(
            username='fake_username', email='fake_email@qed.ai')
        self.cas_user = CASUser.objects.create(
            user=self.user, universal_id='fake_universal_id')
        self.auth = {'universal_id': 'fake_universal_id'}

        response = self.perform_auth(self.auth)

        self.assertEqual(response.data, {
            'detail': 'Scope claim can_blah is missing'
        })
        self.assertEqual(response.status_code, 403)

    def test_auth_permission_denied(self):
        self.user = get_user_model().objects.create_user(
            username='fake_username', email='fake_email@qed.ai')
        self.cas_user = CASUser.objects.create(
            user=self.user, universal_id='fake_universal_id')
        self.auth = {'universal_id': 'fake_universal_id', 'can_bla': False}

        response = self.perform_auth(self.auth)

        self.assertEqual(response.data, {
            'detail': 'Scope claim can_blah is missing'
        })
        self.assertEqual(response.status_code, 403)
