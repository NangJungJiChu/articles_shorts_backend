from rest_framework import generics
from .serializers import UserSerializer
from django.contrib.auth import get_user_model

# Create your views here.
User = get_user_model()

class SignupView(generics.CreateAPIView):
    queryset = User.objects.all()
    serializer_class = UserSerializer
