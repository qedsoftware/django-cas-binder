from django.contrib.auth import get_user_model
from django.db import transaction
from django_cas_binder.models import CASUser


@transaction.atomic
def create_user_and_casuser(username, email, universal_id):
    # user will have an "unusable" password
    u = get_user_model().objects.create_user(username, email)
    CASUser.objects.create(universal_id=universal_id, user=u)
    return u
