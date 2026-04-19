from django.urls import path
from .views import GalleryListCreateView, GalleryDeleteView, GalleryNoteView

urlpatterns = [
    path("photos", GalleryListCreateView.as_view()),
    path("photos/<str:photo_id>", GalleryDeleteView.as_view()),
    path("photos/<str:photo_id>/note", GalleryNoteView.as_view()),
]
