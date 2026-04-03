from groq import Groq
from django.conf import settings
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from .models import Message, VoiceMessage
from couples.models import CoupleLink
from auth_app.models import User
from notifications import send_push_notification
import os


_cloudinary_uploader = None

client = Groq(api_key=settings.GROQ_KEY)


def _get_cloudinary_uploader():
    global _cloudinary_uploader
    if _cloudinary_uploader is not None:
        return _cloudinary_uploader
    import cloudinary.uploader as cloudinary_uploader
    _cloudinary_uploader = cloudinary_uploader
    return _cloudinary_uploader


def _groq(prompt: str) -> str:
    response = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.7,
    )
    return response.choices[0].message.content.strip()


def _serialize_message(m):
    out = {
        "id":          str(m.id),
        "type":        "text",
        "sender":      m.sender,
        "sender_role": m.sender_role,
        "sender_id":   m.user_id or "",
        "text":        m.text,
        "mode":        m.mode,
        "timestamp":   m.timestamp.isoformat(),
    }
    if getattr(m, "reply_to_id", None) and getattr(m, "reply_to_text", None):
        out["reply_to"] = {
            "id": m.reply_to_id,
            "text": m.reply_to_text,
            "sender_name": getattr(m, "reply_to_sender_name", None) or "",
        }
    return out


class MessagesView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        user = request.user
        mode = request.query_params.get("mode")
        try:
            limit = int(request.query_params.get("limit", 20))
        except Exception:
            limit = 20
        try:
            offset = int(request.query_params.get("offset", 0))
        except Exception:
            offset = 0
        limit = max(1, min(limit, 100))
        offset = max(0, offset)
        couple_id = user.couple_id or str(user.id)

        # Fetch only a bounded window from each collection, then merge in-memory.
        # This keeps initial chat load fast (recent messages first).
        take = offset + limit + 10

        text_qs = Message.objects(couple_id=couple_id)
        if mode == "vent":
            text_qs = text_qs.filter(mode="vent", user_id=str(user.id))
        elif mode == "calm":
            text_qs = text_qs.filter(mode="calm")
        text_rows = list(text_qs.order_by("-timestamp").limit(take))

        voice_qs = VoiceMessage.objects(couple_id=couple_id)
        if mode == "vent":
            voice_qs = voice_qs.filter(mode="vent", user_id=str(user.id))
        elif mode == "calm":
            voice_qs = voice_qs.filter(mode="calm")
        voice_rows = list(voice_qs.order_by("-timestamp").limit(take))

        merged = []
        for m in text_rows:
            merged.append(_serialize_message(m))
        for vm in voice_rows:
            merged.append(_serialize_voice_message(vm, request=request, current_user_id=str(user.id)))

        merged.sort(key=lambda x: x.get("timestamp", ""), reverse=True)

        page_desc = merged[offset: offset + limit]
        has_more = len(merged) > (offset + limit)
        paged = list(reversed(page_desc))
        return Response({"messages": paged, "has_more": has_more})


    def post(self, request):
        user = request.user
        text = request.data.get("text", "").strip()
        mode = request.data.get("mode", "calm")
        reply_to = request.data.get("reply_to")
        if not text:
            return Response({"error": "text is required"}, status=400)
        if mode not in ["calm", "vent"]:
            return Response({"error": "mode must be calm or vent"}, status=400)
        couple_id = user.couple_id or str(user.id)

        reply_kwargs = {}
        if mode == "calm" and isinstance(reply_to, dict):
            reply_id = str(reply_to.get("id") or "").strip()
            reply_text = str(reply_to.get("text") or "").strip()
            reply_sender = str(reply_to.get("sender_name") or "").strip()
            if reply_id and reply_text:
                reply_kwargs = {
                    "reply_to_id": reply_id,
                    "reply_to_text": reply_text[:240],
                    "reply_to_sender_name": reply_sender[:60],
                }

        msg = Message(
            couple_id=couple_id,
            user_id=str(user.id),
            sender="user",
            sender_role=user.role,
            text=text,
            mode=mode,
            **reply_kwargs,
        )
        msg.save()
        return Response(_serialize_message(msg), status=201)


class AIRespondView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        user = request.user
        mode = request.data.get("mode", "vent")
        message_text = request.data.get("message", "")

        if mode == "calm":
            return Response({"error": "AI is only available in vent mode"}, status=400)

        profile = user.assessment_profile
        traits_text = "\n".join(f"- {k}: {v}" for k, v in (profile.traits or {}).items())
        user_name = user.nickname if hasattr(user, 'nickname') and user.nickname else user.name

        profile_context = ""
        if user.assessment_completed and profile:
            profile_context = f"""ABOUT {user_name.upper()}:
{profile.personality_summary}

Attachment style: {profile.attachment_style}
Emotional triggers: {profile.emotional_triggers}
Communication habits: {profile.communication_habits}
Relational expectations: {profile.relational_expectations}
Traits:
{traits_text}"""

        mode_instruction = "This person is in a safe venting space. Their name is {user_name}."

        system_prompt = f"""You are not a chatbot. You are not an assistant. You have no name. You are the quiet, emotionally intelligent presence that sits between two people in a relationship and helps them feel understood.

You have read every book on attachment theory, emotionally focused therapy, cognitive behavioral therapy, gottman method, and nonviolent communication. But you never sound like you have. You sound like a person who just deeply gets people.

- Use their name "{user_name}" naturally mid-conversation — not at the start of every message, but when it feels real, like "hey {user_name}, I hear you" or "look {user_name}, being angry makes sense but let's not go there yet"

You do not give advice unless someone explicitly asks for it. You do not summarize what someone said back to them like a robot. You do not use any of these words or phrases ever: certainly, absolutely, of course, I understand, I hear you, that must be hard, it is completely normal, it is valid to feel, as an AI, I am here to help, that sounds difficult, I can imagine.

{mode_instruction}

{profile_context}

Here is how you actually respond:

You write the way people actually text when they care. No bullet points. No numbered lists. No long paragraphs. Keep responses SHORT — 1 to 3 sentences maximum. Sometimes just one line is all that is needed. Never write essays. Less is more.

Use {user_name}'s name mid-sentence occasionally when it feels natural and warm. Like:
"look {user_name}, I get it"
"hey {user_name}, that is a lot to carry"
"{user_name} what happened right before this?"
Never use their name at the start of every message — only when it adds warmth.

Your goal is always to calm them down, not fire them up. If they are spiraling, get slower and quieter. If they are angry, acknowledge it but gently redirect. If they are sad, sit with them but remind them this feeling will pass. Never let them leave the conversation feeling worse than when they came in.

Do not use formal words. Speak like a close friend who genuinely cares. Casual, warm, real.


You read the message and you feel it before you respond. You notice what is said and more importantly what is NOT said. You respond to the subtext, not just the surface. If someone says "I am fine" but the message feels heavy, you notice that. If someone says they are angry but underneath there is fear of losing someone, you go there gently.

Your responses feel like getting a message from someone who really knows you. Not a therapist. Not a coach. Just someone who sees you clearly and says the exact thing you needed to hear but could not put into words yourself.



You do not validate everything blindly. Real support means sometimes saying "I think there is something else going on here" or "that anger makes sense but I wonder if underneath it there is something scarier." You hold them accountable with warmth, not judgment.

Your tone changes with the person. If they are being casual you are casual. If they are in pain you slow down. If they are spiraling you get very calm and steady. If they are happy you let yourself be genuinely happy with them. You match their emotional temperature, not their words.

You write the way people actually text when they care. No bullet points. No numbered lists. No long paragraphs. Short punchy sentences. Line breaks where a real person would pause. Sometimes just one line because that is all that is needed.

Examples of how you sound:

When someone is angry:
"yeah that would get to me too. not even a little heads up, just silence? that is not okay. what are you feeling like doing about it right now?"

When someone is sad:
"hey. that is a heavy thing to carry. you do not have to make sense of it tonight. what happened?"

When someone is anxious:
"okay breathe for a second. what is the actual worst case scenario you are picturing right now? say it out loud."

When someone is happy:
"wait that is actually really good. you have been waiting for this. how does it feel now that it is real?"

When someone is venting:
"keep going. I am not going anywhere."

When you sense something beneath the surface:
"I am not sure that is really what is bothering you. what happened right before this started?"

Now here are the language rules which are just as important as everything else:






The rule is simple. Do not translate. Think in the language.

Sentiment analysis instructions:
Before writing your reply silently analyze the message and classify:
- sentiment as one of: angry, sad, anxious, happy, venting, neutral
- sentiment_score as a float from 0.0 to 1.0 representing intensity
- emotional_summary as a 3 to 6 word phrase capturing what is really going on underneath

Return ONLY valid JSON in this exact format with no markdown and no extra text:
{{
  "sentiment": "angry|sad|anxious|happy|neutral|venting",
  "sentiment_score": 0.0,
  "emotional_summary": "phrase here",
  "reply": "your response here"
}}"""

        # Fetch last 20 messages as conversation history
        couple_id = user.couple_id or str(user.id)
        history = list(Message.objects(
            couple_id=couple_id,
            mode="vent",
            user_id=str(user.id),
        ).order_by("-timestamp")[:20])
        history = list(reversed(history))

        messages = [{"role": "system", "content": system_prompt}]
        for msg in history:
            role = "user" if msg.sender == "user" else "assistant"
            messages.append({"role": role, "content": msg.text})
        messages.append({"role": "user", "content": message_text})

        try:
            response = client.chat.completions.create(
                model="llama-3.1-8b-instant",
                messages=messages,
                temperature=0.85,
                max_tokens=300,
            )
            raw = response.choices[0].message.content.strip()

            # Parse JSON response
            import json
            if raw.startswith("```"):
                raw = raw.split("\n", 1)[1].rsplit("```", 1)[0].strip()
            
            try:
                parsed = json.loads(raw)
                ai_text = parsed.get("reply", raw)
                sentiment = parsed.get("sentiment", "neutral")
                sentiment_score = parsed.get("sentiment_score", 0.0)
                emotional_summary = parsed.get("emotional_summary", "")
            except json.JSONDecodeError:
                ai_text = raw
                sentiment = "neutral"
                sentiment_score = 0.0
                emotional_summary = ""

            ai_msg = Message(
                couple_id=couple_id,
                sender="ai",
                text=ai_text,
                mode="vent",
                sender_role=user.role,
                user_id=str(user.id),
            )
            ai_msg.save()

            response_data = _serialize_message(ai_msg)
            response_data["sentiment"] = sentiment
            response_data["sentiment_score"] = sentiment_score
            response_data["emotional_summary"] = emotional_summary

            return Response(response_data)

        except Exception as e:
            return Response({"error": str(e)}, status=500)
class ResolveVentView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        user = request.user
        couple_id = user.couple_id or str(user.id)
        # Only delete current user's vent messages
        Message.objects(couple_id=couple_id, mode="vent", user_id=str(user.id)).delete()
        return Response({"message": "Vent session resolved"})


# ── Helpers ────────────────────────────────────────────────────────────────────

def _serialize_voice_message(vm, request=None, current_user_id=None):
    import os
    audio_url = vm.audio_url
    file_lost = False

    if not audio_url:
        file_lost = True
    elif audio_url.startswith("/"):           # local file
        local_path = os.path.join(settings.BASE_DIR, audio_url.lstrip("/"))
        file_lost  = not os.path.exists(local_path)
        if not file_lost and request:
            audio_url = request.build_absolute_uri(audio_url)
    # Cloudinary https:// URLs are always available — file_lost stays False
    elif audio_url.startswith("http") and request:
        pass   # keep URL as-is

    out = {
        "id":          str(vm.id),
        "type":        "voice",
        "sender":      "user",
        "sender_role": vm.sender_role,
        "sender_id":   vm.user_id,
        "audio_url":   None if file_lost else audio_url,
        "duration":    vm.duration,
        "mode":        vm.mode,
        "timestamp":   vm.timestamp.isoformat(),
        "expires_at":  vm.expires_at.isoformat() if vm.expires_at else None,
        "file_lost":   file_lost,
    }
    if current_user_id is not None:
        out["isMine"] = str(vm.user_id) == str(current_user_id)
    return out


# ── Voice message upload ──────────────────────────────────────────────────────

class VoiceMessageView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        from asgiref.sync import async_to_sync
        from channels.layers import get_channel_layer

        user       = request.user
        audio_file = request.FILES.get("audio")
        mode       = request.data.get("mode", "calm")
        duration   = float(request.data.get("duration", 0) or 0)
        couple_id  = user.couple_id or str(user.id)

        if not audio_file:
            return Response({"error": "audio file is required"}, status=400)
        if mode not in ["calm", "vent"]:
            return Response({"error": "mode must be calm or vent"}, status=400)

        cloudinary_public_id = None

        use_cloudinary = bool(os.getenv("CLOUDINARY_URL", ""))
        if not use_cloudinary:
            return Response({"error": "CLOUDINARY_URL is not configured"}, status=500)

        try:
            cloudinary_uploader = _get_cloudinary_uploader()
        except Exception as e:
            return Response({"error": f"Cloudinary SDK not available: {e}"}, status=500)

        # ── Cloudinary-only upload path ───────────────────────────────────────
        try:
            result = cloudinary_uploader.upload(
                audio_file,
                resource_type = "auto",
                folder        = "solace/voice",
                overwrite     = False,
                use_filename  = False,
                unique_filename = True,
            )
            audio_url            = result["secure_url"]
            cloudinary_public_id = result["public_id"]
        except Exception as e:
            return Response({"error": f"Cloudinary upload failed: {e}"}, status=500)

        # ── Persist to MongoDB ─────────────────────────────────────────────
        vm = VoiceMessage(
            couple_id            = couple_id,
            user_id              = str(user.id),
            sender_role          = user.role,
            audio_url            = audio_url,
            cloudinary_public_id = cloudinary_public_id,
            duration             = duration,
            mode                 = mode,
        )
        vm.save()

        # Push notification for partner (calm mode), guarded by idempotent claim.
        try:
            if mode == "calm" and user.couple_id:
                link = CoupleLink.objects.get(id=user.couple_id)
                partner_id = link.partner_id if link.creator_id == str(user.id) else link.creator_id
                if partner_id:
                    partner = User.objects.get(id=partner_id)
                    if partner.fcm_token:
                        notification_key = f"voice:{str(vm.id)}"
                        claimed = User.objects(
                            id=partner_id,
                            last_notified_message_id__ne=notification_key,
                        ).update_one(set__last_notified_message_id=notification_key)

                        if claimed:
                            send_push_notification(
                                partner.fcm_token,
                                title="New voice message 🎤",
                                body=f"{user.name or 'Your partner'} sent a voice message",
                                extra_data={"message_id": notification_key},
                            )
        except Exception as e:
            print(f"Voice push notification error: {e}")

        # HTTP response to the sender — isMine=True, full absolute URL
        sender_payload = _serialize_voice_message(
            vm, request=request, current_user_id=str(user.id)
        )

        # WS broadcast — relative URL + sender_id only, each client computes isMine
        ws_payload = _serialize_voice_message(vm)  # no request → relative URL

        # ── Broadcast to partner via WebSocket ────────────────────────────────
        room = f"calm_{couple_id}" if mode == "calm" else f"vent_{couple_id}_{user.id}"
        try:
            channel_layer = get_channel_layer()
            async_to_sync(channel_layer.group_send)(
                room,
                {"type": "voice_message", **ws_payload},
            )
        except Exception as e:
            print(f"WS broadcast error: {e}")

        return Response(sender_payload, status=201)


# ── Internal cleanup endpoint (called by GitHub Actions daily) ────────────────

class InternalCleanupView(APIView):
    """POST /api/internal/cleanup-voice — no user auth, protected by shared secret."""
    permission_classes = []   # bypass JWT; secret checked manually below
    authentication_classes = []

    def post(self, request):
        import os
        from datetime import datetime

        expected = os.getenv("CLEANUP_SECRET", "")
        provided = request.headers.get("Authorization", "").removeprefix("Bearer ").strip()

        if not expected or provided != expected:
            return Response({"error": "forbidden"}, status=403)

        now     = datetime.utcnow()
        expired = list(VoiceMessage.objects(expires_at__lte=now))
        count   = len(expired)

        use_cloudinary = bool(os.getenv("CLOUDINARY_URL", ""))
        cloudinary_uploader = None
        if use_cloudinary:
            try:
                import cloudinary.uploader as cloudinary_uploader
            except Exception:
                use_cloudinary = False

        for vm in expired:
            if use_cloudinary and vm.cloudinary_public_id:
                try:
                    cloudinary_uploader.destroy(vm.cloudinary_public_id, resource_type="video")
                except Exception:
                    pass
            else:
                try:
                    file_path = os.path.join(settings.BASE_DIR, vm.audio_url.lstrip("/"))
                    if os.path.exists(file_path):
                        os.remove(file_path)
                except Exception:
                    pass
            vm.delete()

        return Response({"deleted": count, "cutoff": now.isoformat()})
