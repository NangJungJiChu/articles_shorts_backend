from rest_framework import generics
from .serializers import UserSerializer
from django.contrib.auth import get_user_model
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.parsers import MultiPartParser, FormParser
from PIL import Image
from io import BytesIO
from django.core.files.base import ContentFile
from django.conf import settings
from django.shortcuts import redirect
import requests

# Create your views here.

class SignupView(generics.CreateAPIView):
    def get_queryset(self):
        return get_user_model().objects.all()
    serializer_class = UserSerializer

class UserDetailView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        return Response({
            'username': request.user.username,
            'email': request.user.email,
            'profile_img': request.user.profile_img.url if request.user.profile_img else None,
            'is_pass_verified': request.user.is_pass_verified,
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

class PassVerificationView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        # Mock PASS verification
        user = request.user
        user.is_pass_verified = True
        user.save()
        return Response({'message': 'PASS verification successful', 'is_pass_verified': True})

    def get(self, request):
        return Response({'is_pass_verified': request.user.is_pass_verified})

class KakaoLoginView(APIView):
    permission_classes = [AllowAny]
    def get(self, request):
        kakao_auth_url = "https://kauth.kakao.com/oauth/authorize"
        client_id = settings.KAKAO_REST_API_KEY
        redirect_uri = settings.KAKAO_REDIRECT_URI
        next_path = request.GET.get('next', '/profile')
        
        # Capture current user ID to persist across the redirect
        user_id = request.user.id if request.user.is_authenticated else ""
        # Store as "user_id|next_path"
        state = f"{user_id}|{next_path}"

        # If key is missing and we are in DEBUG, provide a Mock URL
        if not client_id and settings.DEBUG:
            mock_url = f"http://localhost:8000/accounts/api/kakao/mock-auth/?redirect_uri={redirect_uri}&state={state}"
            return Response({'url': mock_url, 'is_mock': True})
            
        if not client_id:
            return Response({'error': 'KAKAO_REST_API_KEY is not configured in .env'}, status=500)
            
        # Using 'state' to pass the return path AND user identification through Kakao
        url = f"{kakao_auth_url}?client_id={client_id}&redirect_uri={redirect_uri}&response_type=code&scope=account_email,age_range&state={state}"
        return Response({'url': url})

class KakaoMockAuthView(APIView):
    permission_classes = [AllowAny]
    def get(self, request):
        if not settings.DEBUG:
            return Response({'error': 'Not Found'}, status=404)
        redirect_uri = request.GET.get('redirect_uri')
        state = request.GET.get('state', '|')
        mock_code = "sample_mock_auth_code_123"
        return redirect(f"{redirect_uri}?code={mock_code}&is_mock=true&state={state}")

class KakaoCallbackView(APIView):
    permission_classes = [AllowAny]
    def get(self, request):
        code = request.GET.get('code')
        is_mock = request.GET.get('is_mock') == 'true'
        
        if not code:
            return Response({'error': 'No code provided'}, status=400)
            
        if is_mock and settings.DEBUG:
            # Simulate Kakao's response for a 25-year-old user
            kakao_account = {
                'email': 'mockuser@example.com',
                'age_range': '20~29'
            }
            access_token = 'mock_access_token'
        else:
            # 1. Exchange code for access token
            token_url = "https://kauth.kakao.com/oauth/token"
            data = {
                'grant_type': 'authorization_code',
                'client_id': settings.KAKAO_REST_API_KEY,
                'redirect_uri': settings.KAKAO_REDIRECT_URI,
                'code': code,
            }
            token_res = requests.post(token_url, data=data)
            token_data = token_res.json()
            access_token = token_data.get('access_token')
            
            if not access_token:
                return Response({'error': 'Failed to get access token', 'details': token_data}, status=400)
                
            # 2. Get user info
            user_info_url = "https://kapi.kakao.com/v2/user/me"
            headers = {'Authorization': f'Bearer {access_token}'}
            user_res = requests.get(user_info_url, headers=headers)
            user_data = user_res.json()
            kakao_account = user_data.get('kakao_account', {})
        age_range = kakao_account.get('age_range') # "20~29", "10~14" etc.
        
        # 3. Verify age (19+ check)
        is_adult = False
        if age_range:
            try:
                start_age = int(age_range.split('~')[0])
                if start_age >= 20: 
                    is_adult = True
            except:
                pass
        
        # 4. Find/Create User and Login
        email = kakao_account.get('email')
        
        # Parse state: "user_id|next_path"
        state_raw = request.GET.get('state', '|')
        try:
            stored_user_id, next_path = state_raw.split('|', 1)
        except ValueError:
            stored_user_id, next_path = "", "/profile"

        frontend_base = settings.KAKAO_FRONTEND_REDIRECT_URI.split('/profile')[0]
        redirect_to = f"{frontend_base}{next_path}"

        if not email:
            return redirect(f"{redirect_to}?verification=fail&reason=no_email")
            
        if not is_adult:
            return redirect(f"{redirect_to}?verification=fail&reason=underage")

        # Get or create user
        User = get_user_model()
        user = None
        
        # Priority 1: Use the stored user ID from the state (persisted across redirect)
        if stored_user_id:
            try:
                user = User.objects.get(id=stored_user_id)
                # Link the email if it wasn't there
                if not user.email:
                    user.email = email
            except User.DoesNotExist:
                pass
        
        # Priority 2: Find by email or create new if not linked yet
        if not user:
            try:
                user = User.objects.get(email=email)
            except User.DoesNotExist:
                import uuid
                username = f"kakao_{str(uuid.uuid4())[:8]}"
                user = User.objects.create_user(username=username, email=email)
        
        # Mark as verified
        user.is_pass_verified = True
        user.save()
        
        # Generate JWT Tokens
        from rest_framework_simplejwt.tokens import RefreshToken
        refresh = RefreshToken.for_user(user)
        access_token = str(refresh.access_token)
        refresh_token = str(refresh)
        
        return redirect(f"{redirect_to}?verification=success&access={access_token}&refresh={refresh_token}")


class UserDeleteView(APIView):
    permission_classes = [IsAuthenticated]

    def delete(self, request):
        user = request.user
        
        # Hard delete or Soft delete? 
        # For "Withdrawal", usually hard delete or permanent deactivation.
        # Let's do hard delete for this MVP.
        user.delete()
        
        return Response({'message': 'Account deleted successfully'}, status=status.HTTP_204_NO_CONTENT)

class PasswordChangeView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        user = request.user
        old_password = request.data.get('old_password')
        new_password = request.data.get('new_password')
        
        if not old_password or not new_password:
            return Response({'error': 'Both old and new passwords are required'}, status=status.HTTP_400_BAD_REQUEST)
            
        if not user.check_password(old_password):
            return Response({'error': 'Invalid old password'}, status=status.HTTP_400_BAD_REQUEST)
            
        user.set_password(new_password)
        user.save()
        
        # Updating password logs out all other sessions (invalidates session auth), 
        # but for JWT, the old tokens remain valid until expiration unless we use a blacklist.
        # For this MVP, we just update the password.
        
        return Response({'message': 'Password updated successfully'}, status=status.HTTP_200_OK)
