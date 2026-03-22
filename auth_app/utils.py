import jwt
import bcrypt
from datetime import datetime, timedelta
from django.conf import settings


def hash_password(plain: str) -> str:
    return bcrypt.hashpw(plain.encode(), bcrypt.gensalt()).decode()


def check_password(plain: str, hashed: str) -> bool:
    return bcrypt.checkpw(plain.encode(), hashed.encode())


def generate_tokens(user_id: str) -> dict:
    now = datetime.utcnow()
    access_payload = {
        "user_id": user_id,
        "exp": now + timedelta(days=settings.JWT_ACCESS_EXPIRY_DAYS),
        "iat": now,
        "type": "access",
    }
    refresh_payload = {
        "user_id": user_id,
        "exp": now + timedelta(days=settings.JWT_REFRESH_EXPIRY_DAYS),
        "iat": now,
        "type": "refresh",
    }
    return {
        "access": jwt.encode(access_payload, settings.JWT_SECRET, algorithm="HS256"),
        "refresh": jwt.encode(refresh_payload, settings.JWT_SECRET, algorithm="HS256"),
    }


def decode_token(token: str) -> dict:
    return jwt.decode(token, settings.JWT_SECRET, algorithms=["HS256"])
