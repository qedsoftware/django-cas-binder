"""CAS authentication backend.

Mostly copied from django_cas_ng.
"""

from __future__ import absolute_import
from __future__ import unicode_literals

from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.auth.backends import ModelBackend
from django.db import transaction
from django_cas_ng.signals import cas_user_authenticated
from django_cas_ng.utils import get_cas_client

from django_cas_binder.models import CASUser
from django_cas_binder.utils import get_free_username
from django_cas_binder.create_user_and_casuser import create_user_and_casuser


USERNAME_TRIES_LIMIT = 1000


__all__ = ['CASBinderBackend']


class CASBinderBackend(ModelBackend):
    """CAS authentication backend"""

    def __init__(self):
        self.user_model = get_user_model()

    def clean_username(self, current_username, new_username):
        def is_username_free(username):
            return not self.user_model.objects.filter(
                username=username).exists()

        if current_username is not None and current_username == new_username:
            return current_username
        else:
            return get_free_username(
                new_username, is_username_free, USERNAME_TRIES_LIMIT)

    @transaction.atomic
    def update_user_attributes(self, user, attributes):
        update_attributes = getattr(
            settings, 'CAS_BINDER_UPDATE_USER_ATTRIBUTES', [])
        for attr in update_attributes:
            if attr in attributes:
                setattr(user, attr, attributes[attr])
        user.save()

    def authenticate(self, ticket, service, request=None):
        """Verifies CAS ticket and gets or creates user object"""
        client = get_cas_client(service_url=service)
        universal_id, attributes, pgtiou = client.verify_ticket(ticket)

        if attributes and request:
            request.session['attributes'] = attributes
        if not universal_id:
            return None

        try:
            user = CASUser.objects.get(universal_id=universal_id).user
            attributes['username'] = self.clean_username(
                user.username, attributes['username'])
            self.update_user_attributes(user, attributes)
            created = False
        except CASUser.DoesNotExist:
            # check if we want to create new users, if we don't fail auth
            if not settings.CAS_CREATE_USER:
                return None

            attributes['username'] = self.clean_username(
                None, attributes['username'])

            user = create_user_and_casuser(
                attributes['username'], attributes['email'], universal_id
            )
            user.save()
            created = True

        if not self.user_can_authenticate(user):
            return None

        if pgtiou and settings.CAS_PROXY_CALLBACK and request:
            request.session['pgtiou'] = pgtiou

        # send the `cas_user_authenticated` signal
        cas_user_authenticated.send(
            sender=self,
            user=user,
            created=created,
            attributes=attributes,
            ticket=ticket,
            service=service,
        )
        return user

    def get_user(self, user_id):
        """Retrieve the user's entry in the user model if it exists"""

        try:
            return self.user_model.objects.get(pk=user_id)
        except self.user_model.DoesNotExist:
            return None

    def user_can_authenticate(self, user):
        """Added for compatibility with older Django versions (1.9), which
        don't implement user_can_authenticate.

        Field `active` is not considered here. CAS server should care for that.
        """
        return True
