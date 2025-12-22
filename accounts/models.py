from django.db import models
from django.contrib.auth.models import AbstractUser
from pgvector.django import VectorField

# Create your models here.
class User(AbstractUser):
    gender = models.CharField(max_length=10, null=True, blank=True)
    age = models.IntegerField(null=True, blank=True)
    profile_img = models.CharField(max_length=255, null=True, blank=True)
    
    # Recommendation System Fields
    preference_vector = VectorField(dimensions=768, null=True, blank=True) # Content-Based (SBERT)
    cf_latent_vector = VectorField(dimensions=64, null=True, blank=True)   # Collaborative Filtering (MF)
    interested_categories = models.ManyToManyField('posts.Category', related_name='interested_users', blank=True)

    class Meta:
        db_table = 'accounts_user'