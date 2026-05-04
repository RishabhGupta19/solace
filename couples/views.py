import random
import string
from datetime import datetime
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from .models import CoupleLink, CalendarMemory
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


class SetRelationshipStartDateView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        user = request.user
        couple_id = getattr(user, "couple_id", None) or str(user.id)
        start_date_str = request.data.get("start_date")

        if not start_date_str:
            return Response({"error": "start_date is required"}, status=400)

        try:
            start_date = datetime.fromisoformat(start_date_str.replace('Z', '+00:00'))
        except (ValueError, AttributeError):
            return Response({"error": "Invalid date format. Use ISO format."}, status=400)

        link = CoupleLink.objects(id=couple_id).first()
        if not link:
            link = CoupleLink(code="#SOLO" + str(user.id)[:8], creator_id=str(user.id))

        link.relationship_start_date = start_date
        link.save()

        return Response({"message": "Relationship start date set", "start_date": start_date.isoformat()})

    def get(self, request):
        user = request.user
        couple_id = getattr(user, "couple_id", None) or str(user.id)
        link = CoupleLink.objects(id=couple_id).first()

        if not link or not link.relationship_start_date:
            return Response({"start_date": None})

        return Response({"start_date": link.relationship_start_date.isoformat()})


class CalendarMemoriesListView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        user = request.user
        couple_id = getattr(user, "couple_id", None) or str(user.id)
        
        year = request.query_params.get("year")
        month = request.query_params.get("month")

        if not year or not month:
            return Response({"error": "year and month parameters required"}, status=400)

        try:
            year, month = int(year), int(month)
        except ValueError:
            return Response({"error": "year and month must be integers"}, status=400)

        from datetime import timedelta
        start = datetime(year, month, 1)
        if month == 12:
            end = datetime(year + 1, 1, 1)
        else:
            end = datetime(year, month + 1, 1)

        memories = CalendarMemory.objects(
            couple_id=couple_id,
            date__gte=start,
            date__lt=end
        ).order_by("date")

        return Response({
            "memories": [
                {
                    "id": str(m.id),
                    "date": m.date.date().isoformat(),
                    "title": m.title,
                    "note": m.note,
                    "emoji": m.emoji,
                    "photo_ids": m.photo_ids,
                    "created_by": m.created_by,
                    "created_at": m.created_at.isoformat(),
                }
                for m in memories
            ]
        })


class CalendarMemoryDetailView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        user = request.user
        couple_id = getattr(user, "couple_id", None) or str(user.id)
        
        date_str = request.data.get("date")
        title = request.data.get("title", "A memory")
        note = request.data.get("note", "")
        emoji = request.data.get("emoji", "❤️")
        photo_ids = request.data.get("photo_ids", [])

        if not date_str:
            return Response({"error": "date is required"}, status=400)

        try:
            date_obj = datetime.fromisoformat(date_str.replace('Z', '+00:00'))
        except (ValueError, AttributeError):
            return Response({"error": "Invalid date format"}, status=400)

        memory = CalendarMemory.objects(couple_id=couple_id, date=date_obj).first()
        
        if not memory:
            memory = CalendarMemory(
                couple_id=couple_id,
                date=date_obj,
                created_by=str(user.id)
            )

        memory.title = title
        memory.note = note
        memory.emoji = emoji
        memory.photo_ids = photo_ids
        memory.updated_at = datetime.utcnow()
        memory.save()

        return Response({
            "id": str(memory.id),
            "date": memory.date.date().isoformat(),
            "title": memory.title,
            "note": memory.note,
            "emoji": memory.emoji,
            "photo_ids": memory.photo_ids,
            "created_by": memory.created_by,
        })

    def delete(self, request):
        user = request.user
        couple_id = getattr(user, "couple_id", None) or str(user.id)
        
        date_str = request.query_params.get("date")

        if not date_str:
            return Response({"error": "date query parameter required"}, status=400)

        try:
            date_obj = datetime.fromisoformat(date_str.replace('Z', '+00:00'))
        except (ValueError, AttributeError):
            return Response({"error": "Invalid date format"}, status=400)

        memory = CalendarMemory.objects(couple_id=couple_id, date=date_obj).first()
        
        if not memory:
            return Response({"error": "Memory not found"}, status=404)

        memory.delete()
        return Response({"message": "Memory deleted"})
