"""
URL configuration for njjc project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/6.0/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import path, include
from .views import health_check
from accounts.views import KakaoLoginView, KakaoCallbackView, KakaoMockAuthView

urlpatterns = [
    path('health/', health_check, name='health_check'),
    path('admin/', admin.site.urls),
    path('posts/', include('posts.urls')), 
    path('accounts/api/kakao/login/', KakaoLoginView.as_view(), name='kakao_login_direct'),
    path('accounts/api/kakao/mock-auth/', KakaoMockAuthView.as_view(), name='kakao_mock_auth_direct'),
    path('accounts/api/kakao/callback/', KakaoCallbackView.as_view(), name='kakao_callback_direct'),
    path('accounts/', include('accounts.urls')),
] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)