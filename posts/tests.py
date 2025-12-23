from django.test import TestCase
from django.contrib.auth import get_user_model
from .models import Post, Category, UserInteraction

User = get_user_model()

class SignalTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='testuser', password='password')
        self.category = Category.objects.create(id='test_cat', name='Test Category')
        self.post = Post.objects.create(
            author=self.user,
            category=self.category,
            title='Test Post',
            content='Test Content'
        )

    def test_like_unlike_signal(self):
        # 1. Like the post
        self.post.like_users.add(self.user)
        
        # Verify interaction created
        self.assertEqual(UserInteraction.objects.filter(
            user=self.user, 
            post=self.post, 
            interaction_type='LIKE'
        ).count(), 1)

        # 2. Unlike the post
        self.post.like_users.remove(self.user)

        # Verify interaction deleted
        # This will fail until we implement the signal handler
        self.assertEqual(UserInteraction.objects.filter(
            user=self.user, 
            post=self.post, 
            interaction_type='LIKE'
        ).count(), 0)
