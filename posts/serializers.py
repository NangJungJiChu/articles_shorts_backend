from rest_framework import serializers
from .models import Post, Category, Comment


class CategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = Category
        fields = ['id', 'name']


class CommentSerializer(serializers.ModelSerializer):
    author_username = serializers.CharField(source='author.username', read_only=True)
    author_profile_image = serializers.ImageField(source='author.profile_img', read_only=True)

    class Meta:
        model = Comment
        fields = ['id', 'content', 'author_username', 'author_profile_image', 'created_at']


class PostListSerializer(serializers.ModelSerializer):
    author_username = serializers.CharField(source='author.username', read_only=True)
    author_profile_image = serializers.ImageField(source='author.profile_img', read_only=True)
    category_name = serializers.CharField(source='category.name', read_only=True)
    like_count = serializers.IntegerField(source='like_users.count', read_only=True)
    comments = CommentSerializer(source='comment_set', many=True, read_only=True)
    is_liked = serializers.SerializerMethodField()

    class Meta:
        model = Post
        fields = [
            'id',
            'title',
            'content',
            'author_username',
            'author_profile_image',
            'category',
            'category_name',
            'is_nsfw',
            'is_profane',
            'created_at',
            'like_count',
            'comments',
            'is_liked',
        ]

    def get_is_liked(self, obj):
        request = self.context.get('request')
        if request and request.user.is_authenticated:
            # Note: This might hit DB per post. For strict optimization, use Exists subquery in View.
            # But for now, we rely on basic implementation.
            return obj.like_users.filter(id=request.user.id).exists()
        return False
