from django.urls import path
from . import views

urlpatterns = [    
    # category list
    path('categories/', views.CategoryListView.as_view(), name='category_list_create'),

    # post list (with pagination)
    path('', views.PostListView.as_view(), name='post_list'),
    
    # recommended post list
    path('recommended/', views.RecommendedPostListView.as_view(), name='post_recommended'),
    path('<int:post_id>/similar/', views.SimilarPostListView.as_view(), name='post_similar'),

    # My page APIs
    path('my/', views.MyPostListView.as_view(), name='my_post_list'),
    path('my/likes/', views.MyLikedPostListView.as_view(), name='my_liked_post_list'),

    # image upload
    path('api/upload/image/', views.ImageUploadView.as_view(), name='image_upload'),

    # like toggle, comments
    path('<int:post_id>/like/', views.LikeToggleView.as_view(), name='post_like'),
    path('<int:post_id>/interact/', views.PostInteractionView.as_view(), name='post_interact'),
    path('<int:post_id>/report/', views.ReportPostView.as_view(), name='post_report'),
    path('<int:post_id>/comments/', views.PostCommentView.as_view()),

    # search posts
    path('search-posts/', views.PostSearchView.as_view()),
    path('search/semantic/', views.SemanticPostSearchView.as_view(), name='post_search_semantic'),

    # post detail
    path('detail/<int:post_id>/', views.PostDetailView.as_view()),

    # create post
    path('create/', views.PostCreateView.as_view()),
    
    # delete post
    path('delete/<int:post_id>/', views.PostDeleteView.as_view()),
]