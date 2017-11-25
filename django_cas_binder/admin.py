import csv

import requests
from django.conf import settings
from django.http import HttpResponse
from django.contrib import admin, messages
from django.contrib.auth import get_user_model
from django.contrib.auth.admin import UserAdmin
from django.db import transaction
from django.core.exceptions import SuspiciousOperation

from django_cas_binder.models import CASUser


class UniversalIdsApiError(Exception):
    def __init__(self, messages):
        self.messages = messages


MAX_ERRORS_TO_SHOW = 7


def fetch_universal_ids_from_cas(emails):
    r = requests.post(
        settings.CAS_SERVER_URL + 'api/universal_ids/',
        json={'emails': emails})
    if r.status_code == 200:
        return r.json()['universal_ids']
    else:
        messages = []
        for error in r.json()['errors'][:MAX_ERRORS_TO_SHOW]:
            if error.get('error_code') == 'no_such_user':
                messages.append('%s - %s' % (
                    error['email'], error['error_message']
                ))
            else:
                messages.append(error['error_message'])
        more_errors = r.json()['errors'][MAX_ERRORS_TO_SHOW:]
        if more_errors:
            messages.append('%d other errors occurred' % len(more_errors))
        raise UniversalIdsApiError(messages)


class CasAwareUserAdmin(UserAdmin):
    actions = UserAdmin.actions + ['export_users', 'enable_cas_login']

    def get_actions(self, request):
        actions = super().get_actions(request)
        if not request.user.is_superuser:
            if 'export_users' in actions:
                del actions['export_users']
            if 'enable_cas_login' in actions:
                del actions['enable_cas_login']
        return actions

    def export_users(self, request, queryset):
        if not request.user.is_superuser:
            raise SuspiciousOperation(
                'CasAwareUserAdmin.export_users attempted by a non-superuser.')
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = 'attachment; filename="users.csv"'

        writer = csv.writer(response)
        for user in queryset:
            writer.writerow([user.email, user.username, user.password])

        return response
    export_users.short_description = u"Export users as CSV."

    def enable_cas_login(self, request, queryset):
        if not request.user.is_superuser:
            raise SuspiciousOperation(
                'CasAwareUserAdmin.enable_cas_login attempted by a '
                'non-superuser.')
        try:
            email_to_universal_id = fetch_universal_ids_from_cas(
                [u.email for u in queryset])
        except UniversalIdsApiError as e:
            for message in e.messages:
                self.message_user(request, message, messages.ERROR)
            return

        for user in queryset:
            email = user.email
            universal_id = email_to_universal_id[email]
            with transaction.atomic():
                cas_user = CASUser.objects \
                    .select_for_update() \
                    .filter(user=user).first()
                if cas_user is None:
                    CASUser.objects.create(user=user, universal_id=universal_id)
                else:
                    cas_user.universal_id = universal_id
                    cas_user.save()
    enable_cas_login.short_description = u"Enable cas - populate universal ids"


admin.site.register(CASUser)
# safe to use get_user_model() here, because at least from Django 1.7 on the
# django.contrib.admin.autodiscover() is called after all apps have been loaded
admin.site.unregister(get_user_model())
admin.site.register(get_user_model(), CasAwareUserAdmin)
