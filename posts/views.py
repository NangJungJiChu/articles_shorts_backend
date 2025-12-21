from django.http import JsonResponse
from django.shortcuts import get_object_or_404
from django.db.models import Q
from .models import Post, Category, Comment
from django.contrib.auth import get_user_model # 유저 모델 가져오기
from django.views.decorators.csrf import csrf_exempt # CSRF 면제 데코레이터
import json
from rest_framework.decorators import api_view, permission_classes, authentication_classes
from rest_framework.authentication import TokenAuthentication
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.pagination import PageNumberPagination
from rest_framework.generics import ListAPIView
from rest_framework_simplejwt.authentication import JWTAuthentication
import os
import uuid
from django.conf import settings
from rest_framework import generics, views, status
from rest_framework.parsers import MultiPartParser, FormParser
from .serializers import CategorySerializer, PostListSerializer, CommentSerializer
import boto3
from botocore.exceptions import NoCredentialsError
import traceback
from PIL import Image
from io import BytesIO

class CategoryListView(generics.ListAPIView):
    queryset = Category.objects.all().order_by('name')
    serializer_class = CategorySerializer
    pagination_class = None


class PostPagination(PageNumberPagination):
    page_size = 10
    page_size_query_param = 'page_size'
    max_page_size = 100


class PostListView(ListAPIView):
    queryset = Post.objects.select_related('author', 'category').prefetch_related(
        'like_users', 'comment_set', 'comment_set__author'
    ).order_by('-created_at')
    serializer_class = PostListSerializer
    pagination_class = PostPagination

class RecommendedPostListView(ListAPIView):
    # Randomly order posts to simulate recommendation system
    queryset = Post.objects.select_related('author', 'category').prefetch_related(
        'like_users', 'comment_set', 'comment_set__author'
    ).order_by('?')
    serializer_class = PostListSerializer
    pagination_class = PostPagination


class MyPostListView(ListAPIView):
    serializer_class = PostListSerializer
    pagination_class = PostPagination
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return Post.objects.filter(author=self.request.user).select_related('author', 'category').prefetch_related(
        'like_users', 'comment_set', 'comment_set__author'
    ).order_by('-created_at')


class MyLikedPostListView(ListAPIView):
    serializer_class = PostListSerializer
    pagination_class = PostPagination
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return Post.objects.filter(like_users=self.request.user).select_related('author', 'category').prefetch_related(
        'like_users', 'comment_set', 'comment_set__author'
    ).order_by('-created_at')


class ImageUploadView(views.APIView):
    parser_classes = (MultiPartParser, FormParser)

    def post(self, request, *args, **kwargs):
        # Handle multiple files
        files = request.FILES.getlist('image')
        if not files:
            return Response({"error": "No image provided"}, status=status.HTTP_400_BAD_REQUEST)

        try:
            s3 = boto3.client(
                's3',
                aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
                aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
                region_name=settings.AWS_S3_REGION_NAME
            )
        except Exception as e:
            print(f"Boto3 Client Init Error: {e}")
            return Response({"error": "AWS Credentials Error (See console)"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        results = []

        import concurrent.futures

        def process_and_upload(file_obj):
            try:
                # Force .png extension
                ext = '.png'
                file_id = str(uuid.uuid4())
                filename = f"{file_id}{ext}"

                # Seek to start if reusing file
                if hasattr(file_obj, 'seek'):
                    file_obj.seek(0)
                
                # 1. Open image using Pillow
                image = Image.open(file_obj)
                
                # 2. Convert to RGBA (if not already)
                if image.mode not in ('RGB', 'RGBA'):
                    image = image.convert('RGBA')
                
                # 3. Save as PNG to memory buffer
                buffer = BytesIO()
                image.save(buffer, format="PNG")
                buffer.seek(0)
                
                # 4. Upload buffer to S3
                s3.upload_fileobj(
                    buffer,
                    settings.AWS_STORAGE_BUCKET_NAME,
                    filename,
                    ExtraArgs={
                        "ContentType": "image/png"
                    }
                )

                # Construct URL
                file_url = f"https://{settings.AWS_STORAGE_BUCKET_NAME}.s3.{settings.AWS_S3_REGION_NAME}.amazonaws.com/{filename}"
                
                return {
                    "id": file_id,
                    "url": file_url
                }
            except Exception as e:
                print(f"Error processing file {file_obj.name}: {e}")
                traceback.print_exc()
                return None

        # Use ThreadPoolExecutor to upload files in parallel
        results = []
        with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
            # Map files to the helper function
            future_results = list(executor.map(process_and_upload, files))
        
        # Filter out None results (failed uploads)
        results = [r for r in future_results if r is not None]

        if not results:
             return Response({"error": "Upload failed"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        # Backward compatibility: if single file uploaded, return single object
        
        # If multiple, return list
        return Response(results, status=status.HTTP_201_CREATED)


class LikeToggleView(views.APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, post_id):
        post = get_object_or_404(Post, pk=post_id)
        user = request.user

        if post.like_users.filter(id=user.id).exists():
            post.like_users.remove(user)
            is_liked = False
        else:
            post.like_users.add(user)
            is_liked = True
        
        return Response({
            'is_liked': is_liked,
            'like_count': post.like_users.count()
        })


class PostCommentView(views.APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, post_id):
        post = get_object_or_404(Post, pk=post_id)
        comments = Comment.objects.filter(post_id=post_id).select_related('author').order_by('created_at')
        serializer = CommentSerializer(comments, many=True)
        return Response({
            'count': comments.count(),
            'comments': serializer.data
        })
    
    def post(self, request, post_id):
        post = get_object_or_404(Post, pk=post_id)
        content = request.data.get('content')
        if not content:
            return Response({'error': '내용을 입력해주세요.'}, status=status.HTTP_400_BAD_REQUEST)
        
        comment = Comment.objects.create(
            post=post,
            author=request.user,
            content=content
        )
        
        # Return serialized newly created comment
        serializer = CommentSerializer(comment)
        return Response(serializer.data, status=status.HTTP_201_CREATED)


class PostSearchView(views.APIView):
    permission_classes = [IsAuthenticated]
    def get(self, request):
        query = request.query_params.get('q', '')
        if not query:
            return Response({'error': '검색어(q)가 필요합니다.'}, status=status.HTTP_400_BAD_REQUEST)
        
        # 제목에 키워드가 포함된 글 찾기
        posts = Post.objects.filter(title__icontains=query).values('id', 'title', 'author__username')[:5]
        
        return Response({
            'count': len(posts),
            'results': list(posts)
        })

class PostDetailView(views.APIView):
    permission_classes = [IsAuthenticated]
    def get(self, request, post_id):
        # 게시글 상세 조회 (없으면 404)
        post = get_object_or_404(Post, pk=post_id)
        
        data = {
            'id': post.id,
            'title': post.title,
            'author': post.author.username,
            'category': post.category_id,
            'body': post.content,  # 요약에 필요한 본문
            'score': post.like_users.count(),
        }
        return Response(data)


class PostCreateView(views.APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        # DRF는 request.data로 JSON을 바로 읽습니다.
        title = request.data.get('title')
        body = request.data.get('body')
        category_id = request.data.get('category', 'mildlyinteresting')

        if not title or not body:
            return Response({'error': '제목과 본문은 필수입니다.'}, status=status.HTTP_400_BAD_REQUEST)

        # request.user는 토큰을 통해 인증된 유저입니다.
        post = Post.objects.create(
            title=title,
            content=body,
            category_id=category_id,
            author=request.user 
        )

        return Response({
            'message': '인증된 계정으로 작성되었습니다.',
            'post_id': post.id,
            'author': request.user.username
        }, status=status.HTTP_201_CREATED)

