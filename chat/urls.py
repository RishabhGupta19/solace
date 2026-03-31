from django.urls import path
from .views import MessagesView, AIRespondView, ResolveVentView, VoiceMessageView, InternalCleanupView

urlpatterns = [
    path("messages",                    MessagesView.as_view()),
    path("messages/voice",              VoiceMessageView.as_view()),
    path("chat/ai-respond",             AIRespondView.as_view()),
    path("chat/resolve",                ResolveVentView.as_view()),
    path("internal/cleanup-voice",      InternalCleanupView.as_view()),
]
