import mongoengine as me
from datetime import datetime


class AssessmentProfile(me.EmbeddedDocument):
    raw_answers = me.ListField(me.DictField(), default=list)
    personality_summary = me.StringField(default="")
    attachment_style = me.StringField(default="")
    emotional_triggers = me.StringField(default="")
    communication_habits = me.StringField(default="")
    relational_expectations = me.StringField(default="")
    traits = me.DictField(default=dict)
    generated_at = me.DateTimeField(default=datetime.utcnow)


class User(me.Document):
    name = me.StringField(required=True)
    email = me.StringField(required=True, unique=True)
    password = me.StringField(required=True)
    nickname = me.StringField(default="")
    onboarding_complete = me.BooleanField(default=False)
    fcm_token = me.StringField(default="")
    last_notified_message_id = me.StringField(default="")
    role = me.StringField(choices=["gf", "bf"], default=None)
    couple_id = me.StringField(default=None)
    partner_name = me.StringField(default=None)
    is_linked = me.BooleanField(default=False)
    assessment_completed = me.BooleanField(default=False)
    assessment_profile = me.EmbeddedDocumentField(AssessmentProfile, default=AssessmentProfile)
    # Profile picture stored on Cloudinary: {'url': str, 'public_id': str}
    profilePic = me.DictField(default=dict)
    created_at = me.DateTimeField(default=datetime.utcnow)
    
    # For forgot password by madhu
    # otp = me.StringField()
    # otp_expiry = me.DateTimeField()
    # reset_otp_attempts = me.IntField(default=0)
    # reset_otp_last_sent = me.DateTimeField()
    reset_otp = me.StringField()
    reset_otp_expiry = me.DateTimeField()
    reset_otp_attempts = me.IntField(default=0)
    reset_otp_last_sent = me.DateTimeField()

    # ✅ ADD THESE (VERY IMPORTANT)
    reset_token = me.StringField()
    reset_token_expiry = me.DateTimeField()

    # Keep schema tolerant for rolling deployments where some documents may
    # already contain newly introduced fields.
    meta = {"collection": "users", "strict": False}

    @property
    def is_authenticated(self):
        return True
