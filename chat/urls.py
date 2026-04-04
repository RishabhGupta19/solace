from django.urls import path
from .views import MessagesView, AIRespondView, ResolveVentView, VoiceMessageView, InternalCleanupView, MessageDeleteView, MessageSearchView, MessageContextView

urlpatterns = [
    path("messages",                    MessagesView.as_view()),
    path("messages/search",             MessageSearchView.as_view()),
    path("messages/context",            MessageContextView.as_view()),
    path("messages/<str:message_id>",   MessageDeleteView.as_view()),
    path("messages/voice",              VoiceMessageView.as_view()),
    path("chat/ai-respond",             AIRespondView.as_view()),
    path("chat/resolve",                ResolveVentView.as_view()),
    path("internal/cleanup-voice",      InternalCleanupView.as_view()),
]
