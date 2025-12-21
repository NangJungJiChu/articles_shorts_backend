from django.db import models
from django.conf import settings
from pgvector.django import VectorField

class Category(models.Model):
    # field 컬럼 삭제!
    # 실제 DB에 id 컬럼만 존재하므로, 이것이 PK이자 카테고리명입니다.
    id = models.CharField(max_length=255, primary_key=True) 
    name = models.CharField(max_length=255)

    class Meta:
        db_table = 'posts_category'

class Post(models.Model):
    # 기존 코드 유지
    author = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    category = models.ForeignKey(Category, on_delete=models.CASCADE)
    title = models.CharField(max_length=255)
    content = models.TextField()
    like_users = models.ManyToManyField(settings.AUTH_USER_MODEL, related_name='like_posts')
    is_nsfw = models.BooleanField(default=False)
    is_profane = models.BooleanField(default=False)
    embedding = VectorField(dimensions=768, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'posts_post'
        # managed = False (Post 테이블도 이미 있으면 추가해도 좋습니다)

# Comment 등 다른 모델도 그대로 유지
class Comment(models.Model):
    author = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    post = models.ForeignKey(Post, on_delete=models.CASCADE)
    content = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    parent = models.ForeignKey('self', null=True, on_delete=models.CASCADE)

    class Meta:
        db_table = 'posts_comment'