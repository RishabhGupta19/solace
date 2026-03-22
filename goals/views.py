# from rest_framework.views import APIView
# from rest_framework.response import Response
# from rest_framework.permissions import IsAuthenticated
# from .models import Goal
# from django.core.mail import send_mail
# from auth_app.models import User
# from couples.models import CoupleLink


# def _serialize_goal(g):
#     return {
#         "id": str(g.id),
#         "text": g.text,
#         "tag": g.tag,
#         "setBy": g.set_by,
#         "completed": g.completed,
#         "date": g.date.isoformat(),
#     }


# class GoalsView(APIView):
#     permission_classes = [IsAuthenticated]

#     def get(self, request):
#         user = request.user
#         couple_id = user.couple_id or str(user.id)
#         goals = Goal.objects(couple_id=couple_id)
#         return Response({"goals": [_serialize_goal(g) for g in goals]})

#     def post(self, request):
#         user = request.user
#         couple_id = user.couple_id or str(user.id)
#         text = request.data.get("text", "").strip()
#         tag = request.data.get("tag", "")

#         if not text:
#             return Response({"error": "text is required"}, status=400)

#         VALID_TAGS = {"growth": "Growth", "us": "Us", "personal": "Personal"}
#         tag_normalized = VALID_TAGS.get(tag.lower())
#         if not tag_normalized:
#             return Response({"error": "tag must be Growth, Us, or Personal"}, status=400)

#         goal = Goal(couple_id=couple_id, text=text, tag=tag_normalized, set_by=user.role)
#         goal.save()
#         try:
#             if user.is_linked:
#                 link = CoupleLink.objects(id=couple_id).first()
#                 if link:
#                     partner_id = link.partner_id if link.creator_id == str(user.id) else link.creator_id
#                     if partner_id:
#                         partner = User.objects.get(id=partner_id)
#                         send_mail(
#                             subject=f"💛 {user.name} set a new goal for you both",
#                             message=f"""Hey {partner.name},

#     {user.name} just set a new {tag_normalized} goal:

#     "{text}"

#     Log in to UsTwo to check it out and stay on track together. 💪

#     — The UsTwo Team""",
#                             from_email=None,  # uses DEFAULT_FROM_EMAIL
#                             recipient_list=[partner.email],
#                             fail_silently=True,
#                         )
#         except Exception as e:
#             print(f"Email error: {e}")

#         return Response(_serialize_goal(goal), status=201)


# class ToggleGoalView(APIView):
#     permission_classes = [IsAuthenticated]

#     def patch(self, request, goal_id):
#         try:
#             goal = Goal.objects.get(id=goal_id)
#         except Goal.DoesNotExist:
#             return Response({"error": "Goal not found"}, status=404)
#         goal.completed = not goal.completed
#         goal.save()
#         return Response(_serialize_goal(goal))


# class EditDeleteGoalView(APIView):
#     permission_classes = [IsAuthenticated]

#     def patch(self, request, goal_id):
#         try:
#             goal = Goal.objects.get(id=goal_id)
#         except Goal.DoesNotExist:
#             return Response({"error": "Goal not found"}, status=404)

#         if goal.set_by != request.user.role:
#             return Response({"error": "You can only edit your own goals"}, status=403)

#         text = request.data.get("text", "").strip()
#         tag = request.data.get("tag", "")

#         if text:
#             goal.text = text
#         if tag:
#             VALID_TAGS = {"growth": "Growth", "us": "Us", "personal": "Personal"}
#             tag_normalized = VALID_TAGS.get(tag.lower())
#             if not tag_normalized:
#                 return Response({"error": "tag must be Growth, Us, or Personal"}, status=400)
#             goal.tag = tag_normalized

#         goal.save()
#         return Response(_serialize_goal(goal))

#     def delete(self, request, goal_id):
#         try:
#             goal = Goal.objects.get(id=goal_id)
#         except Goal.DoesNotExist:
#             return Response({"error": "Goal not found"}, status=404)

#         if goal.set_by != request.user.role:
#             return Response({"error": "You can only delete your own goals"}, status=403)

#         goal.delete()
#         return Response({"message": "Goal deleted"})

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from .models import Goal
from django.core.mail import send_mail
from auth_app.models import User
from couples.models import CoupleLink
import threading


def _serialize_goal(g):
    return {
        "id": str(g.id),
        "text": g.text,
        "tag": g.tag,
        "setBy": g.set_by,
        "completed": g.completed,
        "date": g.date.isoformat(),
    }


def _send_goal_email(partner_email, partner_name, user_name, tag_normalized, text):
    try:
        send_mail(
            subject=f"💛 {user_name} set a new goal for you both",
            message=f"""Hey {partner_name},

{user_name} just set a new {tag_normalized} goal:

"{text}"

Log in to check it out and stay on track together. 💪

— The Solace Team""",
            from_email=None,
            recipient_list=[partner_email],
            fail_silently=True,
        )
    except Exception as e:
        print(f"Email error: {e}")


class GoalsView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        user = request.user
        couple_id = user.couple_id or str(user.id)
        goals = Goal.objects(couple_id=couple_id)
        return Response({"goals": [_serialize_goal(g) for g in goals]})

    def post(self, request):
        user = request.user
        couple_id = user.couple_id or str(user.id)
        text = request.data.get("text", "").strip()
        tag = request.data.get("tag", "")

        if not text:
            return Response({"error": "text is required"}, status=400)

        VALID_TAGS = {"growth": "Growth", "us": "Us", "personal": "Personal"}
        tag_normalized = VALID_TAGS.get(tag.lower())
        if not tag_normalized:
            return Response({"error": "tag must be Growth, Us, or Personal"}, status=400)

        goal = Goal(couple_id=couple_id, text=text, tag=tag_normalized, set_by=user.role)
        goal.save()

        # Send email in background thread — does NOT block the response
        try:
            if user.is_linked:
                link = CoupleLink.objects(id=couple_id).first()
                if link:
                    partner_id = link.partner_id if link.creator_id == str(user.id) else link.creator_id
                    if partner_id:
                        partner = User.objects.get(id=partner_id)
                        thread = threading.Thread(
                            target=_send_goal_email,
                            args=(partner.email, partner.name, user.name, tag_normalized, text),
                            daemon=True
                        )
                        thread.start()
        except Exception as e:
            print(f"Email setup error: {e}")

        return Response(_serialize_goal(goal), status=201)


class ToggleGoalView(APIView):
    permission_classes = [IsAuthenticated]

    def patch(self, request, goal_id):
        try:
            goal = Goal.objects.get(id=goal_id)
        except Goal.DoesNotExist:
            return Response({"error": "Goal not found"}, status=404)
        goal.completed = not goal.completed
        goal.save()
        return Response(_serialize_goal(goal))


class EditDeleteGoalView(APIView):
    permission_classes = [IsAuthenticated]

    def patch(self, request, goal_id):
        try:
            goal = Goal.objects.get(id=goal_id)
        except Goal.DoesNotExist:
            return Response({"error": "Goal not found"}, status=404)

        if goal.set_by != request.user.role:
            return Response({"error": "You can only edit your own goals"}, status=403)

        text = request.data.get("text", "").strip()
        tag = request.data.get("tag", "")

        if text:
            goal.text = text
        if tag:
            VALID_TAGS = {"growth": "Growth", "us": "Us", "personal": "Personal"}
            tag_normalized = VALID_TAGS.get(tag.lower())
            if not tag_normalized:
                return Response({"error": "tag must be Growth, Us, or Personal"}, status=400)
            goal.tag = tag_normalized

        goal.save()
        return Response(_serialize_goal(goal))

    def delete(self, request, goal_id):
        try:
            goal = Goal.objects.get(id=goal_id)
        except Goal.DoesNotExist:
            return Response({"error": "Goal not found"}, status=404)

        if goal.set_by != request.user.role:
            return Response({"error": "You can only delete your own goals"}, status=403)

        goal.delete()
        return Response({"message": "Goal deleted"})
