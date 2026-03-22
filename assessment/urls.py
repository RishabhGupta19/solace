from django.urls import path
from .views import GenerateQuestionsView, SubmitAssessmentView

urlpatterns = [
    path("generate-questions", GenerateQuestionsView.as_view()),
    path("submit",             SubmitAssessmentView.as_view()),
]
