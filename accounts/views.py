from rest_framework import generics
from .serializers import UserSerializer
from django.contrib.auth import get_user_model
from rest_framework.permissions import IsAuthenticated
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.parsers import MultiPartParser, FormParser
from PIL import Image
from io import BytesIO
from django.core.files.base import ContentFile

# Create your views here.
User = get_user_model()

class SignupView(generics.CreateAPIView):
    queryset = User.objects.all()
    serializer_class = UserSerializer

class UserDetailView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        return Response({
            'username': request.user.username,
            'email': request.user.email,
            'profile_img': request.user.profile_img.url if request.user.profile_img else None,
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

class ProfileImageUpdateView(APIView):
    permission_classes = [IsAuthenticated]
    parser_classes = (MultiPartParser, FormParser)

    def post(self, request, *args, **kwargs):
        file_obj = request.data.get('file')
        if not file_obj:
            return Response({"error": "No file provided"}, status=status.HTTP_400_BAD_REQUEST)

        try:
            # Open image using Pillow
            image = Image.open(file_obj)
            
            # Resize image to 500x500 (or appropriate size)
            # Use LANCZOS for high quality downsampling
            output_size = (500, 500)
            image = image.resize(output_size, Image.Resampling.LANCZOS)
            
            # Save resized image to BytesIO
            buffer = BytesIO()
            # Convert to RGB if necessary (e.g. for PNG with alpha channel if saving as JPEG)
            # But let's keep original format if possible, or force JPEG/PNG.
            # Determine format from original filename or default to JPEG
            img_format = file_obj.name.split('.')[-1].upper() if '.' in file_obj.name else 'JPEG'
            if img_format == 'JPG': img_format = 'JPEG'
            
            # If PNG/RGBA and saving as JPEG, convert to RGB
            if image.mode in ('RGBA', 'LA') and img_format == 'JPEG':
                background = Image.new('RGB', image.size, (255, 255, 255))
                background.paste(image, mask=image.split()[-1])
                image = background

            image.save(buffer, format=img_format)
            
            # Create a ContentFile
            file_content = ContentFile(buffer.getvalue())
            
            # Generate unique filename
            import uuid
            # file extension
            ext = file_obj.name.split('.')[-1] if '.' in file_obj.name else 'jpg'
            filename = f"user_{request.user.id}_profile.{ext}"
            
            # Save to user model
            user = request.user
            # Delete old image if exists? (Optional, S3 storage with overwrite=True handles overwrites of same name, 
            # but different names might accumulate. For MVP, let's just save.)
            user.profile_img.save(filename, file_content, save=True)
            
            return Response({
                "message": "Profile image updated successfully",
                "url": user.profile_img.url
            }, status=status.HTTP_200_OK)

        except Exception as e:
            import traceback
            traceback.print_exc()
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
