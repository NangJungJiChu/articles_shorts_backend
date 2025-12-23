from django.db import models
from django.contrib.auth.models import AbstractUser
from pgvector.django import VectorField

from .storage import ProfileImageStorage

# Create your models here.
class User(AbstractUser):
    gender = models.CharField(max_length=10, null=True, blank=True)
    age = models.IntegerField(null=True, blank=True)
    # storage needs to be a callable or instance, string reference not supported directly like this in older django or dependent on config
    # Actually Django docs say "A storage object or a callable that returns a storage object."
    profile_img = models.ImageField(upload_to='profile_images/', storage=ProfileImageStorage(), null=True, blank=True)
    
    # Recommendation System Fields
    preference_vector = VectorField(dimensions=768, null=True, blank=True) # Content-Based (SBERT)
    cf_latent_vector = VectorField(dimensions=64, null=True, blank=True)   # Collaborative Filtering (MF)
    interested_categories = models.ManyToManyField('posts.Category', related_name='interested_users', blank=True)

    class Meta:
        db_table = 'accounts_user'

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        
        if self.profile_img:
            try:
                from PIL import Image
                from io import BytesIO
                from django.core.files.base import ContentFile
                
                # Check if the image has already been resized or is being saved for the first time
                # Ideally, we should do this before super().save() to avoid double save, 
                # but we need the file to be present. 
                # However, with S3, opening the file might be slow. 
                # A better approach for S3 is to resize purely in memory before saving if it's a new upload.
                # But since we are overriding save(), self.profile_img might already be an S3Boto3StorageFile
                
                # Let's try to handle it. If it's too complex for save(), signals are better.
                # But for simplicity, let's assume standard behavior first.
                pass 
                # Actually, implementing resize in save() with S3 can be tricky due to re-downloading.
                # Let's do it in the View or Serializer, OR use a signal that checks if the file is new.
                # Given the plan said "in model save/signal", let's use a method we call from the view/serializer
                # or just do it right here but be careful.
            except Exception as e:
                print(f"Error resizing image: {e}")
