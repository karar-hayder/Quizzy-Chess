#!/usr/bin/env python
"""
Test script to verify JWT token validation
"""
import os
import sys
import django

# Setup Django
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "backend.settings")
django.setup()

from rest_framework_simplejwt.tokens import UntypedToken
from django.contrib.auth import get_user_model

User = get_user_model()


def test_jwt_token(token):
    """Test if a JWT token is valid and can be decoded"""
    try:
        validated_token = UntypedToken(token)
        user_id = validated_token.payload.get("user_id")
        print(f"Token payload: {validated_token.payload}")
        print(f"User ID: {user_id}")

        if user_id:
            user = User.objects.get(id=user_id)
            print(f"Found user: {user.username}")
            return True
        else:
            print("No user_id in token payload")
            return False
    except Exception as e:
        print(f"Error validating token: {e}")
        return False


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python test_jwt.py <token>")
        sys.exit(1)

    token = sys.argv[1]
    test_jwt_token(token)
