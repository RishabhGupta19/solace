from django.urls import path
from .views import MessagesView, AIRespondView, ResolveVentView

urlpatterns = [
    path("messages",        MessagesView.as_view()),
    path("chat/ai-respond", AIRespondView.as_view()),
    path("chat/resolve",    ResolveVentView.as_view()),
]
