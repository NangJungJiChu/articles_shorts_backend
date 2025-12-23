from django.urls import path
from rest_framework_simplejwt.views import (
    TokenObtainPairView,
    TokenRefreshView,
)
from . import views

urlpatterns = [
    path('api/token/', TokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('api/token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    path('api/signup/', views.SignupView.as_view(), name='signup'),
    path('api/user/', views.UserDetailView.as_view(), name='user_detail'),
    path('api/user/image/', views.ProfileImageUpdateView.as_view(), name='user_image_update'),
    path('api/onboarding/', views.UserOnboardingView.as_view(), name='user_onboarding'),
]