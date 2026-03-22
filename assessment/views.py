import json
from groq import Groq
from django.conf import settings
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from auth_app.models import AssessmentProfile

client = Groq(api_key=settings.GROQ_KEY)


def _groq(prompt: str) -> str:
    response = client.chat.completions.create(
        model="llama-3.1-8b-instant",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.3,
    )
    text = response.choices[0].message.content.strip()
    if text.startswith("```"):
        text = text.split("\n", 1)[1].rsplit("```", 1)[0].strip()
    return text


def safe_json_loads(text):
    try:
        return json.loads(text)
    except Exception:
        return {"error": "Invalid JSON from model", "raw": text}


class GenerateQuestionsView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        prompt = """You are an experienced relationship counselor and behavioral analyst.
Your task is to generate exactly 10 deeply insightful multiple-choice questions designed to progressively analyze a person's relationship patterns at a psychological level.
The questions must be:
- Interconnected and sequential (each question should subtly build on themes explored in previous ones)
- Designed to uncover deeper layers of behavior, not surface-level preferences
- Focused on communication style, conflict resolution, emotional needs, love language, attachment tendencies, vulnerabilities, and expectations from a partner
Requirements:
- Each question must have 4 to 6 answer options (A-F)
- Each option must represent a distinct behavioral or emotional pattern (avoid overlap)
- Include a mix of scenario-based and introspective questions
- Later questions should probe deeper based on earlier themes (progressive depth)
- Avoid generic or predictable phrasing; questions should feel realistic and psychologically grounded
- Maintain a neutral, non-judgmental tone
Critical Instruction:
- Design the full set of 10 questions as a cohesive assessment flow (not independent questions)
- Ensure responses can later be combined into a detailed personality and relationship profile summary
- The questions should be structured in a way that enables extracting patterns about the user's attachment style, emotional triggers, communication habits, and relational expectations

Return ONLY valid JSON, no markdown, no extra text, in this exact format:
{
  "questions": [
    {
      "id": 1,
      "question": "...",
      "options": ["A. ...", "B. ...", "C. ...", "D. ..."]
    }
  ]
}"""

        try:
            data = safe_json_loads(_groq(prompt))
            return Response(data)
        except Exception as e:
            return Response({"error": str(e)}, status=500)


class SubmitAssessmentView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        user = request.user
        if user.assessment_completed:
            return Response({"error": "Assessment already completed"}, status=400)

        answers = request.data.get("answers", [])
        if not answers:
            return Response({"error": "answers are required"}, status=400)

        answers_text = "\n".join(
            f"Q{i+1}: {a.get('question')} | Selected: {', '.join(a.get('selected', []))}"
            for i, a in enumerate(answers)
        )

        prompt = f"""You are an expert relationship psychologist. Based on the following assessment answers, build a comprehensive personality and relationship profile.

Assessment Answers:
{answers_text}

Return ONLY valid JSON with this exact structure:
{{
  "personality_summary": "A detailed 3-4 sentence paragraph describing this person's overall relationship personality",
  "attachment_style": "One of: Secure / Anxious / Avoidant / Fearful-Avoidant with a 1 sentence explanation",
  "emotional_triggers": "2-3 sentence description of what emotionally triggers this person",
  "communication_habits": "2-3 sentence description of how this person communicates under stress or conflict",
  "relational_expectations": "2-3 sentence description of what this person needs from a partner",
  "traits": {{
    "love_language": "...",
    "conflict_style": "...",
    "emotional_availability": "...",
    "vulnerability_pattern": "...",
    "trust_building": "...",
    "intimacy_style": "..."
  }}
}}"""

        try:
            profile_data = safe_json_loads(_groq(prompt))
            profile = AssessmentProfile(
                raw_answers=answers,
                personality_summary=profile_data.get("personality_summary", ""),
                attachment_style=profile_data.get("attachment_style", ""),
                emotional_triggers=profile_data.get("emotional_triggers", ""),
                communication_habits=profile_data.get("communication_habits", ""),
                relational_expectations=profile_data.get("relational_expectations", ""),
                traits=profile_data.get("traits", {}),
            )
            user.assessment_profile = profile
            user.assessment_completed = True
            user.save()
            return Response({
                "message": "Assessment completed",
                "assessment_profile": {
                    "personality_summary": profile.personality_summary,
                    "attachment_style": profile.attachment_style,
                    "emotional_triggers": profile.emotional_triggers,
                    "communication_habits": profile.communication_habits,
                    "relational_expectations": profile.relational_expectations,
                    "traits": profile.traits,
                }
            })
        except Exception as e:
            return Response({"error": str(e)}, status=500)
