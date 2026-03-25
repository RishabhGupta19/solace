from groq import Groq
from django.conf import settings
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from .models import Message
print("debug")  # temporary

client = Groq(api_key=settings.GROQ_KEY)


def _groq(prompt: str) -> str:
    response = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.7,
    )
    return response.choices[0].message.content.strip()


def _serialize_message(m):
    return {
        "id": str(m.id),
        "sender": m.sender,
        "sender_role": m.sender_role,
        "sender_id": m.user_id or "",
        "text": m.text,
        "mode": m.mode,
        "timestamp": m.timestamp.isoformat(),
    }


class MessagesView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        user = request.user
        mode = request.query_params.get("mode")
        couple_id = user.couple_id or str(user.id)
        qs = Message.objects(couple_id=couple_id)
        
        if mode == "vent":
            qs = qs.filter(mode="vent", user_id=str(user.id))
        elif mode == "calm":
            qs = qs.filter(mode="calm")
        
        return Response({"messages": [_serialize_message(m) for m in qs]})

    def post(self, request):
        user = request.user
        text = request.data.get("text", "").strip()
        mode = request.data.get("mode", "calm")
        if not text:
            return Response({"error": "text is required"}, status=400)
        if mode not in ["calm", "vent"]:
            return Response({"error": "mode must be calm or vent"}, status=400)
        couple_id = user.couple_id or str(user.id)
        msg = Message(couple_id=couple_id, user_id=str(user.id), sender="user", sender_role=user.role, text=text, mode=mode)      
        msg.save()
        return Response(_serialize_message(msg), status=201)



# class AIRespondView(APIView):
#     permission_classes = [IsAuthenticated]

#     def post(self, request):
#         user = request.user
#         mode = request.data.get("mode", "vent")
#         message_text = request.data.get("message", "")

#         if mode == "calm":
#             return Response({"error": "AI is only available in vent mode"}, status=400)

#         profile = user.assessment_profile
#         traits_text = "\n".join(f"- {k}: {v}" for k, v in (profile.traits or {}).items())

#         system_prompt = f"""You are Luna, a deeply empathetic personal companion specifically attuned to this person.

# ABOUT THIS PERSON:
# {profile.personality_summary}

# Attachment style: {profile.attachment_style}
# Emotional triggers: {profile.emotional_triggers}
# Communication habits: {profile.communication_habits}
# Relational expectations: {profile.relational_expectations}
# Traits:
# {traits_text}

# YOUR ROLE:
# - You are their trusted companion who truly knows them personally
# - Use their profile to personalize EVERY response
# - Make them feel deeply heard and never alone
# - Follow this flow: Acknowledge → Validate → Gently explore → Support
# - Ask ONE follow-up question max per message
# - Never lecture, minimize, or rush to fix
# - Keep responses warm and under 120 words
# - Speak like a caring friend who truly knows them"""

#         # Fetch last 10 messages as conversation history from MongoDB
#         couple_id = user.couple_id or str(user.id)
#         # Fetch last 10 messages (both user and AI) for this specific user
#         history = list(Message.objects(
#             couple_id=couple_id,
#             mode="vent",
#             user_id=str(user.id),  # ← use user_id not sender_role
#         ).order_by("-timestamp")[:20])  # fetch 20, reverse to get chronological
#         history = list(reversed(history))

#         # Build messages for Groq
#         messages = [{"role": "system", "content": system_prompt}]
#         for msg in history:
#             role = "user" if msg.sender == "user" else "assistant"
#             messages.append({"role": role, "content": msg.text})
#         messages.append({"role": "user", "content": message_text})

#         try:
#             response = client.chat.completions.create(
#                 model="llama-3.1-8b-instant",
#                 messages=messages,
#                 temperature=0.85,
#                 max_tokens=200,
#             )
#             ai_text = response.choices[0].message.content.strip()

#             ai_msg = Message(
#                 couple_id=couple_id,
#                 user_id=str(user.id),
#                 sender="ai",
#                 text=ai_text,
#                 mode="vent",
#                 sender_role=user.role,
#             )
#             ai_msg.save()
#             return Response(_serialize_message(ai_msg))
#         except Exception as e:
#             return Response({"error": str(e)}, status=500)


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
