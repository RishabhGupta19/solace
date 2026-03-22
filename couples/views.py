import random
import string
from datetime import datetime
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from .models import CoupleLink
from auth_app.models import User


def _generate_code():
    chars = string.ascii_uppercase + string.digits
    return "#" + "".join(random.choices(chars, k=6))


class GenerateCodeView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        user = request.user
        existing = CoupleLink.objects(creator_id=str(user.id)).first()
        if existing:
            return Response({"code": existing.code})

        for _ in range(10):
            code = _generate_code()
            if not CoupleLink.objects(code=code).first():
                break

        link = CoupleLink(code=code, creator_id=str(user.id))
        link.save()
        return Response({"code": code})


class LinkPartnerView(APIView):
    permission_classes = [IsAuthenticated]
    
    def post(self, request):
        user = request.user
        code = request.data.get("code", "").strip().upper()
        partner_name = request.data.get("partner_name", "").strip()

        if not code or not partner_name:
            return Response({"error": "code and partner_name are required"}, status=400)

        if user.is_linked:
            return Response({"error": "Already linked"}, status=400)

        link = CoupleLink.objects(code=code).first()
        if not link:
            return Response({"error": "Invalid code"}, status=404)

        if link.partner_id:
            return Response({"error": "Code already used"}, status=400)

        if link.creator_id == str(user.id):
            return Response({"error": "Cannot link with yourself"}, status=400)
        creator = User.objects.get(id=link.creator_id)
        if creator.is_linked:
            return Response({"error": "This code has already been used"}, status=400)

        couple_id = str(link.id)
        link.partner_id = str(user.id)
        link.linked_at = datetime.utcnow()
        link.save()

        # Update joining user
        user.couple_id = couple_id
        user.partner_name = partner_name
        user.is_linked = True
        user.save()

        # Update creator
        creator = User.objects.get(id=link.creator_id)
        creator.couple_id = couple_id
        creator.partner_name = user.name
        creator.is_linked = True
        creator.save()

        # Migrate solo goals and messages to shared couple_id
        from goals.models import Goal
        from chat.models import Message
        Goal.objects(couple_id=str(user.id)).update(set__couple_id=couple_id)
        Goal.objects(couple_id=str(creator.id)).update(set__couple_id=couple_id)
        Message.objects(couple_id=str(user.id)).update(set__couple_id=couple_id)
        Message.objects(couple_id=str(creator.id)).update(set__couple_id=couple_id)

        return Response({"message": "Successfully linked", "couple_id": couple_id})
