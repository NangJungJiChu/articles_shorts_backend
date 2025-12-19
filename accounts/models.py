from django.db import models
from django.contrib.auth.models import AbstractUser

# Create your models here.
class User(AbstractUser):
    gender = models.CharField(max_length=10, null=True, blank=True)
    age = models.IntegerField(null=True, blank=True)
    profile_img = models.CharField(max_length=255, null=True, blank=True)

    class Meta:
        db_table = 'accounts_user'