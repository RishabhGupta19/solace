from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import AllowAny, IsAuthenticated
from .models import User
from couples.models import CoupleLink
from .utils import hash_password, check_password, generate_tokens, decode_token
import jwt
import random
import string


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
    couple_code = _get_or_create_couple_code(user)
    profile = user.assessment_profile
    
    # Fetch partner's profile picture if linked
    
    if user.is_linked and user.couple_id:
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
        "role": user.role,
        "couple_id": user.couple_id,
        "couple_code": couple_code,
        "partner_name": user.partner_name,
      
        "is_linked": user.is_linked,
        "assessment_completed": user.assessment_completed,
        "assessment_profile": {
            "personality_summary": profile.personality_summary,
            "attachment_style": profile.attachment_style,
            "emotional_triggers": profile.emotional_triggers,
            "communication_habits": profile.communication_habits,
            "relational_expectations": profile.relational_expectations,
            "traits": profile.traits,
        } if user.assessment_completed else None,
        "created_at": user.created_at.isoformat(),
    }
    
# New endpoint to save FCM token
class SaveFCMTokenView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        token = request.data.get("fcm_token", "")
        user = request.user
        user.fcm_token = token
        user.save()
        return Response({"message": "Token saved"})
    
class UpdateProfileView(APIView):
    permission_classes = [IsAuthenticated]

    def put(self, request):
        user = request.user
        nickname = request.data.get("nickname", "").strip()
        if nickname:
            user.nickname = nickname
            user.save()
        return Response({"user": _serialize_user(user)})

class RegisterView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        data = request.data
        name = data.get("name", "").strip()
        email = data.get("email", "").strip().lower()
        password = data.get("password", "")

        if not name or not email or not password:
            return Response({"error": "name, email, and password are required"}, status=400)

        if User.objects(email=email).first():
            return Response({"error": "Email already registered"}, status=400)

        user = User(name=name, email=email, password=hash_password(password))
        user.save()

        # Auto-generate couple code
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
        }, status=201)


class LoginView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        email = request.data.get("email", "").strip().lower()
        password = request.data.get("password", "")
        user = User.objects(email=email).first()
        if not user or not check_password(password, user.password):
            return Response({"error": "Invalid credentials"}, status=401)
        tokens = generate_tokens(str(user.id))
        return Response({"user": _serialize_user(user), **tokens})


class RefreshView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        token = request.data.get("refresh", "")
        try:
            payload = decode_token(token)
        except jwt.ExpiredSignatureError:
            return Response({"error": "Refresh token expired"}, status=401)
        except jwt.InvalidTokenError:
            return Response({"error": "Invalid token"}, status=401)

        if payload.get("type") != "refresh":
            return Response({"error": "Invalid token type"}, status=401)

        try:
            user = User.objects.get(id=payload["user_id"])
        except User.DoesNotExist:
            return Response({"error": "User not found"}, status=404)

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
            return Response({"error": "role must be 'gf' or 'bf'"}, status=400)
        user = request.user
        user.role = role
        user.save()
        return Response({"user": _serialize_user(user)})
