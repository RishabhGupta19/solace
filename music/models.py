import mongoengine as me
from datetime import datetime


class SavedSong(me.Document):
    """
    Stores a music track saved by one member of a couple.
    Scoped to couple_id so both partners share the same library.
    """
    couple_id    = me.StringField(required=True)
    saved_by     = me.StringField(required=True)   # user id who pressed save
    video_id     = me.StringField(required=True)   # song identifier (JioSaavn id or legacy YouTube videoId)
    title        = me.StringField(required=True)
    channel_title = me.StringField(default="")
    thumbnail    = me.StringField(default="")
    audio_url    = me.StringField(default="")       # direct audio stream URL (JioSaavn MP3)
    saved_at     = me.DateTimeField(default=datetime.utcnow)

    meta = {
        "collection": "saved_songs",
        "ordering":   ["-saved_at"],
        "indexes": [
            {"fields": ["couple_id", "video_id"], "unique": True},
        ],
    }
