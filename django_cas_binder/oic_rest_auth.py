import json

import requests
from django.conf import settings
from django_cas_binder.models import CASUser
from oic.oic import Client
from oic.utils.authn.client import CLIENT_AUTHN_METHOD

from rest_framework.authentication import BaseAuthentication
from rest_framework.permissions import BasePermission
from rest_framework.exceptions import AuthenticationFailed


class CASResponseError(Exception):
    pass


class OICAuthentication(BaseAuthentication):
    def authenticate(self, request):
        """Take a request with an 'access_token' query parameter and attempt to
        authenticate them by validating this token using a 'userinfo' endpoint
        in CAS. If succeeded, return a tuple of (user, data) where data is json
        payload received from 'userinfo' endpoint in CAS. It will be a
        dictionary containing 'universal_id' key and {claim_name: True} for each
        scope claim owned by the user. Raise a CASResponseError exception if
        there is some problem with CAS. If access_token is invalid or (local)
        user instance is not found, raise AuthenticationFailed.
        """
        access_token = request.query_params.get('access_token')
        if not access_token:
            return None
        c = Client(client_authn_method=CLIENT_AUTHN_METHOD, verify_ssl=False)
        c.provider_config(settings.CAS_SERVER_URL + 'openid')
        r = requests.get(c._endpoint('userinfo_endpoint'),
                         params={'access_token': access_token})
        if r.status_code == 200:
            resp = json.loads(r.text)
            universal_id = resp.get('universal_id')
            if universal_id is None:
                raise CASResponseError(
                    'cas response contains no universal_id')
            cas_user = CASUser.objects.filter(universal_id=universal_id).first()
            if cas_user is None:
                # FIXME
                raise AuthenticationFailed(
                    'user not found, login to the site with the browser '
                    'and try again'
                )
            return (cas_user.user, resp)
        elif r.status_code in (401, 403):
            msg = r.headers['WWW-Authenticate']
            raise AuthenticationFailed({"detail": msg})
        else:
            response_text = r.text
            response_status_code = r.status_code
            response_headers = r.headers
            raise CASResponseError("CAS returned: {} {} {}".format(
                str(response_status_code),
                str(response_text)[:50],
                str(response_headers)[:20],
            ))


def OICScopeClaimPermissionClass(claim_name):

    class OICScopeClaimPermission(BasePermission):
        message = 'Scope claim ' + claim_name + ' is missing'

        def has_permission(self, request, view):
            return request.auth.get(claim_name) is True
    return OICScopeClaimPermission
