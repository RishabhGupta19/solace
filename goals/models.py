import mongoengine as me
from datetime import datetime


class Goal(me.Document):
    couple_id = me.StringField(required=False, default="solo")
    text = me.StringField(required=True)
    tag = me.StringField(choices=["Growth", "Us", "Personal"], required=True)
    set_by = me.StringField(choices=["gf", "bf"], required=True)
    completed = me.BooleanField(default=False)
    date = me.DateTimeField(default=datetime.utcnow)

    meta = {"collection": "goals", "ordering": ["-date"]}
