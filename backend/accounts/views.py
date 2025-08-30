from django.contrib.auth import login, logout, get_user_model, authenticate
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import permissions
from django.conf import settings
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated, AllowAny
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError as DjangoValidationError
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
        return Response({
            "username": user.username,
            "email": user.email,
            "first_name": user.first_name,  # Add first name
            "last_name": user.last_name,    # Add last name
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
            username = request.data.get("username", "").strip().lower()
            email = request.data.get("email", "").strip().lower()
            password = request.data.get("password")
            first_name = request.data.get("first_name", "").strip().title()  # Capitalize first letter
            last_name = request.data.get("last_name", "").strip().title()    # Capitalize first letter
            invite_code = request.data.get("inviteCode")

            # Validation
            if invite_code != settings.INVITE_CODE:
                return Response({"detail": "Invalid invite code"}, status=400)

            if not username or not email or not password:
                return Response({"detail": "Username, email, and password are required"}, status=400)
            
            # First name is required, last name is optional
            if not first_name:
                return Response({"detail": "First name is required"}, status=400)

            if User.objects.filter(username__iexact=username).exists():
                return Response({"detail": "Username already taken"}, status=400)

            if User.objects.filter(email__iexact=email).exists():
                return Response({"detail": "Email already registered"}, status=400)

            try:
                validate_password(password)
            except DjangoValidationError as e:
                return Response({"detail": list(e.messages)}, status=400)

            # Create user with first/last names
            user = User.objects.create_user(
                username=username,
                email=email,
                password=password,
                first_name=first_name,
                last_name=last_name,
            )

            login(request, user)

            return Response({
                "username": user.username,
                "email": user.email,
                "first_name": user.first_name,
                "last_name": user.last_name,
            }, status=201)

        except Exception as e:
            return Response({
                "detail": "Unexpected error",
                "error": str(e)
            }, status=500)


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
    return redirect(f'/#/password-reset-confirm/{uidb64}/{token}/')
