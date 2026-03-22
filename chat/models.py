import mongoengine as me
from datetime import datetime


class Message(me.Document):
    couple_id = me.StringField(required=False, default="solo")
    user_id = me.StringField(default=None)  # ← add this
    sender = me.StringField(choices=["user", "ai"], required=True)
    sender_role = me.StringField(choices=["gf", "bf"], default=None)
    text = me.StringField(required=True)
    mode = me.StringField(choices=["calm", "vent"], required=True)
    timestamp = me.DateTimeField(default=datetime.utcnow)

    meta = {"collection": "messages", "ordering": ["timestamp"]}
