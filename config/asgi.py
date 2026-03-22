import os
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")

from django.core.asgi import get_asgi_application
from channels.routing import ProtocolTypeRouter, URLRouter
from channels.security.websocket import AllowedHostsOriginValidator
import chat.routing

application = ProtocolTypeRouter({
    "http": get_asgi_application(),
    "websocket": AllowedHostsOriginValidator(
        URLRouter(chat.routing.websocket_urlpatterns)
    ),
})