from django.urls import path
from .views import GoalsView, ToggleGoalView, EditDeleteGoalView

urlpatterns = [
    path("",                          GoalsView.as_view()),
    path("<str:goal_id>/toggle",      ToggleGoalView.as_view()),
    path("<str:goal_id>",             EditDeleteGoalView.as_view()),
]
