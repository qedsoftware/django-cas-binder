from django.contrib.auth.models import User
from django.test import TestCase

from django_cas_binder.assign_universal_ids import assign_universal_ids
from django_cas_binder.models import CASUser


class TestAssignUniversalIDs(TestCase):
    def test_should_skip_nonexistent_user(self):
        assign_universal_ids({"blah@blah.com": "marchew"})

    def test_should_add_casuser_for_existing_user(self):
        user = User.objects.create_user("blah", "blah@blah.com")
        assign_universal_ids({"blah@blah.com": "marchew"})
        cas_user = CASUser.objects.get(user=user)
        self.assertEqual(cas_user.universal_id, "marchew")

    def test_should_update_existing_user(self):
        user = User.objects.create_user("blah", "blah@blah.com")
        cas_user = CASUser.objects.create(user=user, universal_id="placki")
        assign_universal_ids({"blah@blah.com": "marchew"})
        cas_user.refresh_from_db()
        self.assertEqual(cas_user.universal_id, "marchew")
