from django.urls import path
from rest_framework_simplejwt.views import (
    TokenObtainPairView,
    TokenRefreshView,
)
from . import views

urlpatterns = [
    path('api/kakao/login/', views.KakaoLoginView.as_view(), name='kakao_login'),
    path('api/kakao/mock-auth/', views.KakaoMockAuthView.as_view(), name='kakao_mock_auth'),
    path('api/kakao/callback/', views.KakaoCallbackView.as_view(), name='kakao_callback'),
    path('api/token/', TokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('api/token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    path('api/signup/', views.SignupView.as_view(), name='signup'),
    path('api/user/', views.UserDetailView.as_view(), name='user_detail'),
    path('api/user/image/', views.ProfileImageUpdateView.as_view(), name='user_image_update'),
    path('api/onboarding/', views.UserOnboardingView.as_view(), name='user_onboarding'),
    path('api/pass-verification/', views.PassVerificationView.as_view(), name='pass_verification'),
    path('api/user/delete/', views.UserDeleteView.as_view(), name='user_delete'),
    path('api/password/change/', views.PasswordChangeView.as_view(), name='password_change'),
]
