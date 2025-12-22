from rest_framework import generics
from .serializers import UserSerializer
from django.contrib.auth import get_user_model

# Create your views here.
User = get_user_model()

class SignupView(generics.CreateAPIView):
    queryset = User.objects.all()
    serializer_class = UserSerializer

from rest_framework.permissions import IsAuthenticated
from rest_framework.views import APIView
from rest_framework.response import Response

class UserDetailView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        return Response({
            'email': request.user.email,
            # Add other fields if needed
        })

class UserOnboardingView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        category_ids = request.data.get('categories', [])
        if not category_ids:
            return Response({'error': 'Categories are required'}, status=400)
        
        # categories should be a list of IDs
        # Clear existing and add new
        request.user.interested_categories.clear()
        
        # Validating IDs is good practice, but for MVP assuming frontend sends valid IDs
        # or we can filter valid ones locally.
        request.user.interested_categories.add(*category_ids)
        
        return Response({'message': 'Onboarding completed'})
