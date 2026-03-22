import mongoengine as me
from datetime import datetime


class CoupleLink(me.Document):
    code = me.StringField(required=True, unique=True)
    creator_id = me.StringField(required=True)
    partner_id = me.StringField(default=None)
    linked_at = me.DateTimeField(default=None)
    created_at = me.DateTimeField(default=datetime.utcnow)

    meta = {"collection": "couple_links"}
