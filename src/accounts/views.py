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
from django.middleware.csrf import get_token

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
        })


class RegisterView(APIView):
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        try:
            username = request.data.get("username", "").lower()
            email = request.data.get("email", "").lower()
            password = request.data.get("password")
            invite_code = request.data.get("inviteCode")

            if invite_code != settings.INVITE_CODE:
                return Response({"detail": "Invalid invite code"}, status=400)

            if not username or not email or not password:
                return Response({"detail": "All fields are required."}, status=400)

            if User.objects.filter(username__iexact=username).exists():
                return Response({"detail": "Username already taken"}, status=400)

            if User.objects.filter(email__iexact=email).exists():
                return Response({"detail": "Email already registered"}, status=400)

            try:
                validate_password(password)
            except DjangoValidationError as e:
                return Response({"detail": list(e.messages)}, status=400)

            user = User.objects.create_user(
                username=username,
                email=email,
                password=password
            )

            login(request, user)

            return Response({
                "username": user.username,
                "email": user.email,
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
    logout(request)
    request.session.flush()

    # Force session to reinit and new CSRF to be generated
    request.session.cycle_key()  # This triggers creation of a new session ID
    get_token(request)   # This sets a new CSRF token

    return JsonResponse({"detail": "Successfully logged out."})