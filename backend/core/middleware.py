import logging
from urllib.parse import parse_qs

import jwt
from asgiref.sync import sync_to_async
from channels.middleware import BaseMiddleware
from django.conf import settings
from django.contrib.auth.models import AnonymousUser

logger = logging.getLogger(__name__)


class JWTAuthMiddleware(BaseMiddleware):
    async def __call__(self, scope, receive, send):
        from rest_framework_simplejwt.authentication import JWTAuthentication
        from rest_framework_simplejwt.tokens import UntypedToken

        scope["user"] = AnonymousUser()
        try:
            query_string = scope.get("query_string", b"").decode()
            query_params = parse_qs(query_string)
            token = None
            if "token" in query_params:
                token = query_params["token"][0]
                logger.info(
                    f"JWTAuthMiddleware: Found token in query params: {token[:20]}..."
                )
            if not token:
                headers = dict(scope.get("headers", []))
                auth_header = headers.get(b"authorization")
                if auth_header:
                    auth_header = auth_header.decode()
                    if auth_header.startswith("Bearer "):
                        token = auth_header.split(" ", 1)[1]
                        logger.info(
                            f"JWTAuthMiddleware: Found token in headers: {token[:20]}..."
                        )
            if token:
                user = await sync_to_async(self.get_user_from_token)(token)
                scope["user"] = user
                logger.info(
                    f"JWTAuthMiddleware: Authenticated user: {user.username if user.is_authenticated else 'Anonymous'}"
                )
            else:
                logger.warning(
                    "JWTAuthMiddleware: No token found in query params or headers"
                )
        except Exception as e:
            logger.warning(f"JWTAuthMiddleware: Could not authenticate user: {e}")
            scope["user"] = AnonymousUser()
        return await super().__call__(scope, receive, send)

    def get_user_from_token(self, token):
        from django.contrib.auth import get_user_model
        from rest_framework_simplejwt.authentication import JWTAuthentication
        from rest_framework_simplejwt.tokens import UntypedToken

        User = get_user_model()
        try:
            validated_token = UntypedToken(token)
            user_id = validated_token.payload.get("user_id")
            logger.info(
                f"JWTAuthMiddleware: Full token payload: {validated_token.payload}"
            )
            logger.info(f"JWTAuthMiddleware: Decoded token, user_id: {user_id}")
            if user_id:
                user = User.objects.get(id=user_id)
                logger.info(f"JWTAuthMiddleware: Found user: {user.username}")
                return user
            else:
                logger.warning("JWTAuthMiddleware: No user_id in token payload")
                return AnonymousUser()
        except Exception as e:
            logger.error(f"JWTAuthMiddleware: Error decoding token: {e}")
            return AnonymousUser()
