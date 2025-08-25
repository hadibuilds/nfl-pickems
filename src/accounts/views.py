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
from django.contrib.auth.views import PasswordResetView
from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string
from django.utils.html import strip_tags

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
    email_template_name = 'registration/password_reset_email.html'
    subject_template_name = 'registration/password_reset_subject.txt'
    
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
        email_message.send()