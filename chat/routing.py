from django.urls import re_path
from . import consumers

websocket_urlpatterns = [
    re_path(r"ws/chat/(?P<couple_id>[^/]+)/$", consumers.CalmChatConsumer.as_asgi()),
]