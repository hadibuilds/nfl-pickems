from django.contrib.auth import login, logout, get_user_model, authenticate
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import permissions
from django.conf import settings
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated, AllowAny
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError as DjangoValidationError
from django.contrib.auth import authenticate
from django.http import JsonResponse
from django.views.decorators.csrf import ensure_csrf_cookie
from django.shortcuts import redirect
from django.contrib.auth.views import PasswordResetView
from django.contrib.auth.forms import PasswordResetForm, SetPasswordForm
from django.contrib.auth.tokens import default_token_generator
from django.utils.http import urlsafe_base64_decode
from django.utils.encoding import force_str
from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string
from django.utils.html import strip_tags
from rest_framework import status
from rest_framework.parsers import MultiPartParser, FormParser
from django.core.files.storage import default_storage
from django.conf import settings
import os

User = get_user_model()

@ensure_csrf_cookie
@api_view(['GET'])
@permission_classes([AllowAny])
def get_csrf_token(request):
    return JsonResponse({"detail": "CSRF cookie set"})

@api_view(['GET'])
@permission_classes([AllowAny])
def whoami(request):
    user = request.user
    if user.is_authenticated:
        avatar_url = None
        if user.avatar:
            # Use our secure media endpoint instead of direct S3 URL
            avatar_url = request.build_absolute_uri(f'/accounts/secure-media/{user.avatar.name}')
        
        return Response({
            "username": user.username,
            "email": user.email,
            "first_name": user.first_name,
            "last_name": user.last_name,
            "avatar": avatar_url,
        })
    else:
        return Response({"user": None})


class LoginAPIView(APIView):
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        identifier = request.data.get("identifier", "").lower()
        password = request.data.get("password")

        user = None
        if "@" in identifier:
            try:
                user_obj = User.objects.get(email__iexact=identifier)
                user = authenticate(request, username=user_obj.username.lower(), password=password)
            except User.DoesNotExist:
                return Response({"detail": "Invalid email or password"}, status=400)
        else:
            user = authenticate(request, username=identifier.lower(), password=password)

        if not user:
            return Response({"detail": "Invalid credentials"}, status=400)

        login(request, user)
        return Response({
            "username": user.username,
            "email": user.email,
            "first_name": user.first_name,  # Add first name
            "last_name": user.last_name,    # Add last name
        })

class RegisterView(APIView):
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        try:
            username = (request.data.get("username") or "").strip().lower()
            email = (request.data.get("email") or "").strip().lower()
            password = request.data.get("password")
            first_name = (request.data.get("first_name") or "").strip().title()
            last_name = (request.data.get("last_name") or "").strip().title()
            invite_code = request.data.get("inviteCode")  # frontend uses camelCase

            # --- Invite code check (from settings or env) ---
            expected_invite = getattr(settings, "INVITE_CODE", None)
            if not expected_invite:
                return Response(
                    {"detail": "Server misconfigured: invite code not set"},
                    status=500,
                )
            if invite_code != expected_invite:
                return Response({"detail": "Invalid invite code"}, status=400)

            # --- Required fields ---
            if not username or not email or not password:
                return Response(
                    {"detail": "Username, email, and password are required"},
                    status=400,
                )
            if not first_name:
                return Response({"detail": "First name is required"}, status=400)

            # --- Uniqueness checks (case-insensitive) ---
            if User.objects.filter(username__iexact=username).exists():
                return Response({"detail": "Username already taken"}, status=400)
            if User.objects.filter(email__iexact=email).exists():
                return Response({"detail": "Email already registered"}, status=400)

            # --- Password validation ---
            try:
                validate_password(password)
            except DjangoValidationError as e:
                return Response({"detail": list(e.messages)}, status=400)

            # --- Create user ---
            user = User.objects.create_user(
                username=username,
                email=email,
                password=password,
                first_name=first_name,
                last_name=last_name,
            )

            # --- Establish session (authenticate -> login) ---
            authed = authenticate(request, username=username, password=password)
            if authed is None:
                # Fallback: explicitly pass backend (if you know which one you use)
                # login(request, user, backend='django.contrib.auth.backends.ModelBackend')
                return Response(
                    {"detail": "User created but could not log in automatically"},
                    status=201,
                )
            login(request, authed)

            return Response(
                {
                    "username": user.username,
                    "email": user.email,
                    "first_name": user.first_name,
                    "last_name": user.last_name,
                },
                status=201,
            )

        except Exception as e:
            # Log the full error for debugging but don't expose to client
            import logging
            logger = logging.getLogger(__name__)
            logger.exception("Registration error: %s", str(e))
            return Response({"detail": "Registration failed"}, status=500)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
@ensure_csrf_cookie
def logout_view(request):
    try:
        logout(request)
        request.session.flush()

        response = JsonResponse({"detail": "Successfully logged out."})

        # Expire sessionid cookie
        response.delete_cookie(
            key=settings.SESSION_COOKIE_NAME,
            path='/',
            samesite=settings.SESSION_COOKIE_SAMESITE,
        )

        # Expire CSRF cookie
        response.delete_cookie(
            key='csrftoken',
            path='/',
            samesite=settings.CSRF_COOKIE_SAMESITE,
        )

        return response
    except Exception as e:
        # Log error details for debugging
        print(f"Error during logout: {e}")
        return JsonResponse({"detail": "Internal server error"}, status=500)

class CustomPasswordResetView(PasswordResetView):
    """
    Custom password reset view that sends HTML emails
    """
    template_name = 'registration/password_reset_form.html'
    subject_template_name = 'registration/password_reset_subject.txt'
    email_template_name = 'registration/password_reset_email.txt'  # plain text
    html_email_template_name = 'registration/password_reset_email.html'  # HTML
    
    def send_mail(self, subject_template_name, email_template_name,
                  context, from_email, to_email, html_email_template_name=None):
        """
        Send a Django email with both HTML and plain text versions
        """
        subject = render_to_string(subject_template_name, context)
        # Remove newlines from subject
        subject = ''.join(subject.splitlines())
        
        # Render HTML email
        html_content = render_to_string(email_template_name, context)
        
        # Create plain text version by stripping HTML tags
        text_content = strip_tags(html_content)
        
        # Create email with both HTML and text versions
        email_message = EmailMultiAlternatives(
            subject=subject,
            body=text_content,  # Plain text version
            from_email=from_email,
            to=[to_email]
        )
        
        # Attach HTML version
        email_message.attach_alternative(html_content, "text/html")
        
        # Send the email
        result = email_message.send()
        return result

@api_view(['POST'])
@permission_classes([AllowAny])
def password_reset_api(request):
    """
    API endpoint for password reset requests (replaces template view)
    """
    try:
        email = request.data.get('email', '').strip().lower()
        
        if not email:
            return Response({"detail": "Email is required"}, status=status.HTTP_400_BAD_REQUEST)
        
        # Use Django's built-in password reset form for validation and sending
        form = PasswordResetForm({'email': email})
        
        if form.is_valid():
            # This will send the email if user exists
            form.save(
                request=request,
                use_https=request.is_secure(),
                email_template_name='registration/password_reset_email.txt',
                html_email_template_name='registration/password_reset_email.html',
                subject_template_name='registration/password_reset_subject.txt',
            )
            
            # Always return success for security (don't reveal if email exists)
            return Response({
                "detail": "If an account with that email exists, we've sent you a password reset link."
            })
        else:
            return Response({"detail": "Invalid email format"}, status=status.HTTP_400_BAD_REQUEST)
            
    except Exception as e:
        return Response({"detail": "Failed to send reset email"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

@api_view(['POST'])
@permission_classes([AllowAny])
def password_reset_validate_api(request):
    """
    API endpoint to validate password reset token
    """
    try:
        uidb64 = request.data.get('uidb64')
        token = request.data.get('token')
        
        if not uidb64 or not token:
            return Response({"detail": "Invalid parameters"}, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            uid = force_str(urlsafe_base64_decode(uidb64))
            user = User.objects.get(pk=uid)
        except (TypeError, ValueError, OverflowError, User.DoesNotExist):
            return Response({"detail": "Invalid token"}, status=status.HTTP_400_BAD_REQUEST)
        
        if default_token_generator.check_token(user, token):
            return Response({"detail": "Valid token"})
        else:
            return Response({"detail": "Invalid or expired token"}, status=status.HTTP_400_BAD_REQUEST)
            
    except Exception as e:
        return Response({"detail": "Validation failed"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

@api_view(['POST'])
@permission_classes([AllowAny])
def password_reset_confirm_api(request):
    """
    API endpoint to confirm password reset and set new password
    """
    try:
        uidb64 = request.data.get('uidb64')
        token = request.data.get('token')
        new_password1 = request.data.get('new_password1')
        new_password2 = request.data.get('new_password2')
        
        if not all([uidb64, token, new_password1, new_password2]):
            return Response({"detail": "All fields are required"}, status=status.HTTP_400_BAD_REQUEST)
        
        if new_password1 != new_password2:
            return Response({"detail": "Passwords don't match"}, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            uid = force_str(urlsafe_base64_decode(uidb64))
            user = User.objects.get(pk=uid)
        except (TypeError, ValueError, OverflowError, User.DoesNotExist):
            return Response({"detail": "Invalid token"}, status=status.HTTP_400_BAD_REQUEST)
        
        if not default_token_generator.check_token(user, token):
            return Response({"detail": "Invalid or expired token"}, status=status.HTTP_400_BAD_REQUEST)
        
        # Validate password strength
        try:
            validate_password(new_password1, user)
        except DjangoValidationError as e:
            return Response({"detail": list(e.messages)}, status=status.HTTP_400_BAD_REQUEST)
        
        # Set the new password
        user.set_password(new_password1)
        user.save()
        
        return Response({"detail": "Password updated successfully"})
        
    except Exception as e:
        return Response({"detail": "Failed to update password"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

def password_reset_email_redirect(request, uidb64, token):
    """
    Redirect from email links to React frontend with token parameters
    """
    return redirect(f'/password-reset-confirm/{uidb64}/{token}')

@api_view(['PUT', 'PATCH'])
@permission_classes([IsAuthenticated])
def update_profile_api(request):
    """
    API endpoint to update user profile information
    """
    try:
        user = request.user
        data = request.data
        
        # Update profile fields
        if 'first_name' in data:
            user.first_name = data['first_name'].strip().title()
        if 'last_name' in data:
            user.last_name = data['last_name'].strip().title()
        if 'email' in data:
            new_email = data['email'].strip().lower()
            # Check if email is already taken by another user
            if User.objects.filter(email__iexact=new_email).exclude(id=user.id).exists():
                return Response({"detail": "Email already in use"}, status=status.HTTP_400_BAD_REQUEST)
            user.email = new_email
        
        user.save()
        
        # Return updated user data
        avatar_url = None
        if user.avatar:
            # Use our secure media endpoint instead of direct S3 URL
            avatar_url = request.build_absolute_uri(f'/accounts/secure-media/{user.avatar.name}')
        
        return Response({
            "username": user.username,
            "email": user.email,
            "first_name": user.first_name,
            "last_name": user.last_name,
            "avatar": avatar_url,
        })
        
    except Exception as e:
        return Response({"detail": "Failed to update profile"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

class AvatarUploadAPIView(APIView):
    """
    API endpoint for uploading user avatar
    """
    permission_classes = [IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser]
    
    def post(self, request):
        try:
            user = request.user
            
            if 'avatar' not in request.FILES:
                return Response({"detail": "No file provided"}, status=status.HTTP_400_BAD_REQUEST)
            
            avatar_file = request.FILES['avatar']
            
            # Validate file type
            allowed_types = ['image/jpeg', 'image/png', 'image/gif', 'image/webp']
            if avatar_file.content_type not in allowed_types:
                return Response({
                    "detail": "Invalid file type. Only JPEG, PNG, GIF, and WebP are allowed."
                }, status=status.HTTP_400_BAD_REQUEST)
            
            # Validate file size (5MB max)
            max_size = 5 * 1024 * 1024  # 5MB
            if avatar_file.size > max_size:
                return Response({
                    "detail": "File size too large. Maximum size is 5MB."
                }, status=status.HTTP_400_BAD_REQUEST)
            
            # Delete old avatar if exists
            if user.avatar:
                if default_storage.exists(user.avatar.name):
                    default_storage.delete(user.avatar.name)
            
            # Save new avatar
            user.avatar = avatar_file
            user.save()
            
            # Return new avatar URL with cache busting
            import time
            timestamp = int(time.time())
            avatar_url = request.build_absolute_uri(f'/accounts/secure-media/{user.avatar.name}?t={timestamp}')
            return Response({"avatar": avatar_url})
            
        except Exception as e:
            return Response({
                "detail": "Failed to upload avatar"
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    def delete(self, request):
        """Delete user avatar"""
        try:
            user = request.user
            
            if user.avatar:
                if default_storage.exists(user.avatar.name):
                    default_storage.delete(user.avatar.name)
                user.avatar = None
                user.save()
            
            return Response({"detail": "Avatar deleted"})
            
        except Exception as e:
            return Response({
                "detail": "Failed to delete avatar"
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def change_password_api(request):
    """
    API endpoint to change user password
    """
    try:
        user = request.user
        current_password = request.data.get('current_password')
        new_password = request.data.get('new_password')
        
        if not current_password or not new_password:
            return Response({"detail": "Current password and new password are required"}, status=status.HTTP_400_BAD_REQUEST)
        
        # Verify current password
        if not authenticate(username=user.username, password=current_password):
            return Response({"detail": "Current password is incorrect"}, status=status.HTTP_400_BAD_REQUEST)
        
        # Validate new password
        try:
            validate_password(new_password, user)
        except DjangoValidationError as e:
            return Response({"detail": list(e.messages)}, status=status.HTTP_400_BAD_REQUEST)
        
        # Set new password
        user.set_password(new_password)
        user.save()
        
        return Response({"detail": "Password changed successfully"})
        
    except Exception as e:
        return Response({"detail": "Failed to change password"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
