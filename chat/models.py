import mongoengine as me
from datetime import datetime, timedelta


class Message(me.Document):
    couple_id   = me.StringField(required=False, default="solo")
    user_id     = me.StringField(default=None)
    sender      = me.StringField(choices=["user", "ai"], required=True)
    sender_role = me.StringField(choices=["gf", "bf"], default=None)
    seen        = me.BooleanField(default=False)
    seen_at     = me.DateTimeField(default=None)
    text        = me.StringField(required=True)
    reply_to_id = me.StringField(default=None)
    reply_to_text = me.StringField(default=None)
    reply_to_sender_name = me.StringField(default=None)
    mode        = me.StringField(choices=["calm", "vent"], required=True)
    timestamp   = me.DateTimeField(default=datetime.utcnow)

    meta = {"collection": "messages", "ordering": ["timestamp"], "strict": False}


class VoiceMessage(me.Document):
    couple_id            = me.StringField(required=True)
    user_id              = me.StringField(required=True)
    sender_role          = me.StringField(choices=["gf", "bf"], default=None)
    audio_url            = me.StringField(required=True)
    cloudinary_public_id = me.StringField(default=None)   # set when using Cloudinary
    duration             = me.FloatField(default=0.0)
    mode                 = me.StringField(choices=["calm", "vent"], required=True)
    timestamp            = me.DateTimeField(default=datetime.utcnow)
    expires_at           = me.DateTimeField()

    def save(self, *args, **kwargs):
        if not self.expires_at:
            self.expires_at = datetime.utcnow() + timedelta(hours=24)
        return super().save(*args, **kwargs)

    meta = {"collection": "voice_messages", "ordering": ["timestamp"], "strict": False}
