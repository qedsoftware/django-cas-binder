from django.db import models
from django.conf import settings


class CASUser(models.Model):
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        primary_key=True,
    )
    universal_id = models.CharField(max_length=100)
