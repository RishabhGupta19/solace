import mongoengine as me
from datetime import datetime


class GalleryPhoto(me.Document):
    couple_id = me.StringField(required=True)
    uploaded_by = me.StringField(required=True)
    image_url = me.StringField(required=True)
    cloudinary_public_id = me.StringField(default=None)
    note = me.StringField(default=None)
    created_at = me.DateTimeField(default=datetime.utcnow)

    meta = {
        "collection": "gallery_photos",
        "ordering": ["-created_at"],
        "indexes": ["couple_id"],
        "strict": False,
    }
