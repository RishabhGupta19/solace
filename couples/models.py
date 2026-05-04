import mongoengine as me
from datetime import datetime


class CoupleLink(me.Document):
    code = me.StringField(required=True, unique=True)
    creator_id = me.StringField(required=True)
    partner_id = me.StringField(default=None)
    linked_at = me.DateTimeField(default=None)
    relationship_start_date = me.DateTimeField(default=None)
    created_at = me.DateTimeField(default=datetime.utcnow)

    meta = {"collection": "couple_links"}


class CalendarMemory(me.Document):
    couple_id = me.StringField(required=True)
    date = me.DateTimeField(required=True)  # The date the memory is for
    title = me.StringField(default="A memory")  # Memory title
    note = me.StringField(default="")
    emoji = me.StringField(default="❤️")
    photo_ids = me.ListField(me.StringField(), default=[])  # References to GalleryPhoto IDs
    created_by = me.StringField(required=True)
    created_at = me.DateTimeField(default=datetime.utcnow)
    updated_at = me.DateTimeField(default=datetime.utcnow)

    meta = {
        "collection": "calendar_memories",
        "indexes": ["couple_id", "date"],
        "strict": False,
    }
