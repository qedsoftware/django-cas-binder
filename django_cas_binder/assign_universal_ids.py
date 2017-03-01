from django.db import transaction
from django_cas_ng.backends import User

from django_cas_binder.models import CASUser


@transaction.atomic
def assign_universal_ids(mapping):
    for email, universal_id in mapping.items():
        user = User.objects.filter(email=email).first()
        if user is not None:
            cas_user = CASUser.objects.filter(user=user).first()
            if cas_user is None:
                CASUser.objects.create(user=user, universal_id=universal_id)
            else:
                cas_user.universal_id = universal_id
                cas_user.save()
