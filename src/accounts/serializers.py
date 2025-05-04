from rest_framework import serializers
from django.contrib.auth import authenticate
from django.contrib.auth.models import User
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError as DjangoValidationError
from django.conf import settings

class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ("id", "username", "email")

class LoginSerializer(serializers.Serializer):
    identifier = serializers.CharField()
    password = serializers.CharField(write_only=True)

    def validate(self, data):
        identifier = data.get("identifier", "").lower()
        password = data.get("password")

        user = authenticate(username=identifier, password=password)

        if not user:
            try:
                user_obj = User.objects.get(email__iexact=identifier)
                user = authenticate(username=user_obj.username.lower(), password=password)
            except User.DoesNotExist:
                raise serializers.ValidationError("Invalid username/email or password.")

        if not user:
            raise serializers.ValidationError("Invalid credentials.")

        data["user"] = user
        return data

class RegisterSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, validators=[validate_password])

    class Meta:
        model = User
        fields = ("username", "email", "password")

    def create(self, validated_data):
        validated_data["username"] = validated_data["username"].lower()
        validated_data["email"] = validated_data["email"].lower()
        return User.objects.create_user(**validated_data)
