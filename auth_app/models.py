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
    fcm_token = me.StringField(default="")
    role = me.StringField(choices=["gf", "bf"], default=None)
    couple_id = me.StringField(default=None)
    partner_name = me.StringField(default=None)
    is_linked = me.BooleanField(default=False)
    assessment_completed = me.BooleanField(default=False)
    assessment_profile = me.EmbeddedDocumentField(AssessmentProfile, default=AssessmentProfile)
    created_at = me.DateTimeField(default=datetime.utcnow)

    meta = {"collection": "users"}

    @property
    def is_authenticated(self):
        return True
