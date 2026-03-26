from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import AllowAny, IsAuthenticated
from .models import User
from couples.models import CoupleLink
from .utils import hash_password, check_password, generate_tokens, decode_token
import jwt
import random
import string
from rest_framework import status


def _generate_code():
    chars = string.ascii_uppercase + string.digits
    return "#" + "".join(random.choices(chars, k=6))


def _get_or_create_couple_code(user):
    link = CoupleLink.objects(creator_id=str(user.id)).first()
    if not link:
        for _ in range(10):
            code = _generate_code()
            if not CoupleLink.objects(code=code).first():
                break
        link = CoupleLink(code=code, creator_id=str(user.id))
        link.save()
    return link.code


def _serialize_user(user):
    # Ensure we don't raise when optional attributes are missing
  
    if getattr(user, "is_linked", False) and getattr(user, "couple_id", None):
        try:
            link = CoupleLink.objects.get(id=user.couple_id)
            partner_id = link.partner_id if link.creator_id == str(user.id) else link.creator_id
            partner = User.objects.get(id=partner_id)
        
        except (CoupleLink.DoesNotExist, User.DoesNotExist):
            pass
    
    return {
        "id": str(user.id),
        "name": user.name,
        "nickname": user.nickname or "",
        "email": user.email,
        "couple_id": user.couple_id,
        "assessment_completed": getattr(user, "assessment_completed", False),
        "partner_name": user.partner_name,
      
        "is_linked": user.is_linked,
        "assessment_completed": user.assessment_completed,
        "assessment_profile": {
            "personality_summary": getattr(profile, "personality_summary", ""),
            "attachment_style": getattr(profile, "attachment_style", ""),
            "emotional_triggers": getattr(profile, "emotional_triggers", ""),
            "communication_habits": getattr(profile, "communication_habits", ""),
            "relational_expectations": getattr(profile, "relational_expectations", ""),
            "traits": getattr(profile, "traits", {}),
        } if getattr(user, "assessment_completed", False) else None,
    }


class SaveFCMTokenView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        token = request.data.get("fcm_token", "").strip()
        if not token:
            return Response({"error": "fcm_token is required"}, status=status.HTTP_400_BAD_REQUEST)
        user = request.user
        user.fcm_token = token
        user.save()
        return Response({"message": "FCM token saved"})


class RegisterView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        data = request.data or {}
        name = (data.get("name") or "").strip()
        email = (data.get("email") or "").strip().lower()
        password = data.get("password") or ""
        nickname = (data.get("nickname") or "").strip()

        if not name or not email or not password:
            return Response({"error": "name, email and password are required"}, status=status.HTTP_400_BAD_REQUEST)

        if User.objects(email=email).first():
            return Response({"error": "User with this email already exists"}, status=status.HTTP_400_BAD_REQUEST)

        user = User(
            name=name,
            email=email,
            password=hash_password(password),
            nickname=nickname,
        )
        user.save()

        # create a couple link for the user if desired
        for _ in range(10):
            code = _generate_code()
            if not CoupleLink.objects(code=code).first():
                break
        CoupleLink(code=code, creator_id=str(user.id)).save()

        tokens = generate_tokens(str(user.id))
        return Response({
            "message": "Registered successfully",
            "user": _serialize_user(user),
            **tokens,
        }, status=status.HTTP_201_CREATED)


class LoginView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        email = (request.data.get("email") or "").strip().lower()
        password = request.data.get("password") or ""
        user = User.objects(email=email).first()
        if not user or not check_password(password, user.password):
            return Response({"error": "Invalid credentials"}, status=status.HTTP_401_UNAUTHORIZED)
        tokens = generate_tokens(str(user.id))
        response_data = {"user": _serialize_user(user), **tokens}
        # If assessment is completed, instruct client to redirect to dashboard
        if getattr(user, "assessment_completed", False):
            response_data["redirect"] = "/dashboard"
        return Response(response_data)


class RefreshView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        token = request.data.get("refresh", "")
        try:
            payload = decode_token(token)
        except jwt.ExpiredSignatureError:
            return Response({"error": "Refresh token expired"}, status=status.HTTP_401_UNAUTHORIZED)
        except jwt.InvalidTokenError:
            return Response({"error": "Invalid token"}, status=status.HTTP_401_UNAUTHORIZED)

        if payload.get("type") != "refresh":
            return Response({"error": "Invalid token type"}, status=status.HTTP_401_UNAUTHORIZED)

        try:
            user = User.objects.get(id=payload["user_id"])
        except Exception:
            return Response({"error": "User not found"}, status=status.HTTP_404_NOT_FOUND)

        tokens = generate_tokens(str(user.id))
        return Response(tokens)


class MeView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        return Response({"user": _serialize_user(request.user)})


class SetRoleView(APIView):
    permission_classes = [IsAuthenticated]

    def put(self, request):
        role = request.data.get("role")
        if role not in ["gf", "bf"]:
            return Response({"error": "role must be 'gf' or 'bf'"}, status=status.HTTP_400_BAD_REQUEST)
        user = request.user
        user.role = role
        user.save()
        return Response({"user": _serialize_user(user)})
