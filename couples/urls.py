from django.urls import path
from .views import (
    GenerateCodeView, 
    LinkPartnerView, 
    SetRelationshipStartDateView,
    CalendarMemoriesListView,
    CalendarMemoryDetailView
)

urlpatterns = [
    path("generate-code", GenerateCodeView.as_view()),
    path("link", LinkPartnerView.as_view()),
    path("relationship-start-date", SetRelationshipStartDateView.as_view()),
    path("calendar/memories", CalendarMemoriesListView.as_view()),
    path("calendar/memory", CalendarMemoryDetailView.as_view()),
]
