import mongoengine as me
from datetime import datetime


class SavedSong(me.Document):
    """
    Stores a YouTube track saved by one member of a couple.
    Scoped to couple_id so both partners share the same library.
    """
    couple_id    = me.StringField(required=True)
    saved_by     = me.StringField(required=True)   # user id who pressed save
    video_id     = me.StringField(required=True)   # YouTube videoId
    title        = me.StringField(required=True)
    channel_title = me.StringField(default="")
    thumbnail    = me.StringField(default="")
    saved_at     = me.DateTimeField(default=datetime.utcnow)

    meta = {
        "collection": "saved_songs",
        "ordering":   ["-saved_at"],
        "indexes": [
            {"fields": ["couple_id", "video_id"], "unique": True},
        ],
    }
