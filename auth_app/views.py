from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.parsers import MultiPartParser, FormParser
from .models import User
from couples.models import CoupleLink
from .utils import hash_password, check_password, generate_tokens, decode_token
# imports for forgot password
from datetime import datetime, timedelta
from django.core.mail import send_mail
from django.conf import settings
from django.template.loader import render_to_string
from django.utils.html import strip_tags
from django.core.mail import EmailMultiAlternatives
from django.contrib.auth.hashers import make_password

import hashlib

import jwt
import random
import string
import cloudinary.uploader
import secrets


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
    profile = getattr(user, "assessment_profile", None)
    
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
        "onboarding_complete": user.onboarding_complete if hasattr(user, 'onboarding_complete') else False,
        "assessment_profile": {
            "personality_summary": getattr(profile, "personality_summary", ""),
            "attachment_style": getattr(profile, "attachment_style", ""),
            "emotional_triggers": getattr(profile, "emotional_triggers", ""),
            "communication_habits": getattr(profile, "communication_habits", ""),
            "relational_expectations": getattr(profile, "relational_expectations", ""),
            "traits": getattr(profile, "traits", []),
        } if user.assessment_completed and profile else None,
        "created_at": user.created_at.isoformat(),
        # profile picture convenience fields
        "profile_picture_url": (user.profilePic.get('url') if getattr(user, 'profilePic', None) else None),
        "profile_picture_public_id": (user.profilePic.get('public_id') if getattr(user, 'profilePic', None) else None),
        # partner profile picture (if linked and partner exists)
        "partner_profile_picture_url": (partner.profilePic.get('url') if 'partner' in locals() and getattr(partner, 'profilePic', None) else None),
        "partner_profile_picture_public_id": (partner.profilePic.get('public_id') if 'partner' in locals() and getattr(partner, 'profilePic', None) else None),
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
        user.onboarding_complete = True  
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

# view for forgot PAssword feature otp generation
# class ForgotPasswordView(APIView):
#     permission_classes = [AllowAny]

#     def post(self, request):
#         email = request.data.get("email", "").strip().lower()

#         user = User.objects(email=email).first()

#         # Security: don't reveal user existence
#         if not user:
#             return Response({"message": "If email exists, OTP sent"})

#         # Generate OTP
#         otp = str(random.randint(100000, 999999))

#         # Hash OTP
#         hashed_otp = hashlib.sha256(otp.encode()).hexdigest()

#         user.otp = hashed_otp
#         user.otp_expiry = datetime.utcnow() + timedelta(minutes=10)
#         user.save()

#         # Send email
#         # send_mail(
#         #     subject="Password Reset OTP",
#         #     message=f"Your OTP is: {otp}",
#         #     from_email=settings.EMAIL_HOST_USER,
#         #     recipient_list=[email],
#         #     fail_silently=False,
#         # )
#         # Render HTML template
#         html_content = render_to_string(
#             "emails/otp_email.html",
#             {
#                 "otp": otp,
#                 "year": datetime.utcnow().year
#             }
#         )

#         # Fallback plain text
#         text_content = strip_tags(html_content)

#         # Create email
#         email_message = EmailMultiAlternatives(
#             subject="Your Solace OTP Code",
#             body=text_content,
#             from_email=settings.EMAIL_HOST_USER,
#             to=[email],
#         )

#         # Attach HTML
#         email_message.attach_alternative(html_content, "text/html")

#         # Send email
#         email_message.send()

#         return Response({"message": "OTP sent successfully"})
import hashlib, random
from datetime import datetime, timedelta

class ForgotPasswordView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        email = request.data.get("email")
        user = User.objects(email=email).first()

        # ALWAYS SAME RESPONSE
        response_msg = {"message": "If an account exists, an OTP has been sent."}

        if not user:
            return Response(response_msg, status=200)

        now = datetime.utcnow()

        # ⛔ RATE LIMIT (30 sec cooldown)
        if user.reset_otp_last_sent and (now - user.reset_otp_last_sent).seconds < 30:
            return Response({"error": "Please wait before requesting again"}, status=429)

        # 🔢 GENERATE OTP
        otp = str(random.randint(100000, 999999))

        # 🔐 HASH OTP
        hashed_otp = hashlib.sha256(otp.encode()).hexdigest()

        user.reset_otp = hashed_otp
        user.reset_otp_expiry = now + timedelta(minutes=10)
        user.reset_otp_attempts = 0
        user.reset_otp_last_sent = now
        user.save()

        # 📧 SEND EMAIL (your template)
        html_content = render_to_string("emails/otp_email.html", {
            "otp": otp,
            "year": now.year
        })

        text_content = strip_tags(html_content)

        email_message = EmailMultiAlternatives(
            subject="Your Solace OTP Code",
            body=text_content,
            from_email=settings.EMAIL_HOST_USER,
            to=[email],
        )

        email_message.attach_alternative(html_content, "text/html")
        email_message.send()

        return Response(response_msg, status=200)


# view for verify otp for forgot password feature
# class VerifyOTPView(APIView):
#     permission_classes = [AllowAny]

#     def post(self, request):
#         email = request.data.get("email", "").strip().lower()
#         otp = request.data.get("otp", "")

#         user = User.objects(email=email).first()

#         if not user:
#             return Response({"error": "Invalid OTP"}, status=400)

#         hashed_input = hashlib.sha256(otp.encode()).hexdigest()

#         if (
#             user.otp != hashed_input or
#             not user.otp_expiry or
#             user.otp_expiry < datetime.utcnow()
#         ):
#             return Response({"error": "Invalid or expired OTP"}, status=400)

#         return Response({"message": "OTP verified"})
import secrets
from datetime import datetime, timedelta
import hashlib

class VerifyOTPView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        email = request.data.get("email")
        otp = request.data.get("otp")

        user = User.objects(email=email).first()

        if not user or not user.reset_otp:
            return Response({"error": "Invalid OTP"}, status=400)

        if user.reset_otp_attempts >= 5:
            return Response({"error": "Too many attempts. Request new OTP."}, status=429)

        if datetime.utcnow() > user.reset_otp_expiry:
            return Response({"error": "OTP expired"}, status=400)

        hashed_otp = hashlib.sha256(otp.encode()).hexdigest()

        if hashed_otp != user.reset_otp:
            user.reset_otp_attempts += 1
            user.save()
            return Response({"error": "Invalid OTP"}, status=400)

        # ✅ GENERATE TOKEN
        token = secrets.token_urlsafe(32)

        user.reset_token = token
        user.reset_token_expiry = datetime.utcnow() + timedelta(minutes=10)

        # CLEAR OTP
        user.reset_otp = None
        user.reset_otp_expiry = None
        user.reset_otp_attempts = 0

        user.save()

        return Response({
            "message": "OTP verified",
            "token": token
        }, status=200)



# view for reset password for the forgot password feature
# class ResetPasswordView(APIView):
#     permission_classes = [AllowAny]

#     def post(self, request):
#         email = request.data.get("email", "").strip().lower()
#         new_password = request.data.get("new_password", "")

#         user = User.objects(email=email).first()

#         if not user:
#             return Response({"error": "User not found"}, status=400)

#         # Use your existing hashing util
#         user.password = hash_password(new_password)

#         # Clear OTP
#         user.otp = None
#         user.otp_expiry = None

#         user.save()

#         return Response({"message": "Password reset successful"})
class ResetPasswordView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        email = request.data.get("email")
        new_password = request.data.get("new_password")

        user = User.objects(email=email).first()

        if not user:
            return Response({"error": "Invalid request"}, status=400)

        # 🔒 PASSWORD VALIDATION
        if len(new_password) < 6:
            return Response({"error": "Password too short"}, status=400)

        # 🔐 HASH PASSWORD
        user.password = make_password(new_password)

        # 🧹 CLEAR OTP DATA
        user.reset_otp = None
        user.reset_otp_expiry = None
        user.reset_otp_attempts = 0

        user.save()

        return Response({"message": "Password updated successfully"}, status=200)



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


class UploadProfilePicView(APIView):
    permission_classes = [IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser]

    def post(self, request):
        # Expect multipart form with key 'image'
        file = request.FILES.get('image') or request.FILES.get('file')
        if not file:
            return Response({"error": "No file provided"}, status=400)

        # Validate file type
        allowed = ("image/jpeg", "image/jpg", "image/png", "image/webp")
        if file.content_type not in allowed:
            return Response({"error": "Invalid file type"}, status=400)

        # Validate file size (15MB)
        max_size = 15 * 1024 * 1024
        if file.size > max_size:
            return Response({"error": "File too large (max 15MB)"}, status=400)

        user = request.user
        try:
            # If existing picture, remove it from Cloudinary
            existing = getattr(user, 'profilePic', {}) or {}
            public_id = existing.get('public_id')
            if public_id:
                try:
                    cloudinary.uploader.destroy(public_id)
                except Exception:
                    # non-fatal
                    pass

            # Construct a user-based public_id to keep predictable mapping
            unique_id = f"profile_pictures/{str(user.id)}_{int(__import__('time').time())}"

            upload_result = cloudinary.uploader.upload(
                file,
                public_id=unique_id,
                folder="profile_pictures",
                overwrite=True,
                transformation=[{"width": 300, "height": 300, "crop": "fill", "gravity": "face"}],
            )

            url = upload_result.get('secure_url') or upload_result.get('url')
            new_public_id = upload_result.get('public_id')

            user.profilePic = {"url": url, "public_id": new_public_id}
            user.save()

            return Response({"user": _serialize_user(user)})
        except Exception as e:
            return Response({"error": str(e)}, status=500)
