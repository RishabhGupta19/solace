from rest_framework.authentication import BaseAuthentication
from rest_framework.exceptions import AuthenticationFailed
from .utils import decode_token
from .models import User
import jwt


class MongoJWTAuthentication(BaseAuthentication):
    def authenticate(self, request):
        header = request.headers.get("Authorization", "")
        if not header.startswith("Bearer "):
            return None
        token = header.split(" ", 1)[1]
        try:
            payload = decode_token(token)
        except jwt.ExpiredSignatureError:
            raise AuthenticationFailed("Token expired")
        except jwt.InvalidTokenError:
            raise AuthenticationFailed("Invalid token")

        if payload.get("type") != "access":
            raise AuthenticationFailed("Invalid token type")

        try:
            user = User.objects.get(id=payload["user_id"])
        except User.DoesNotExist:
            raise AuthenticationFailed("User not found")

        return (user, token)
