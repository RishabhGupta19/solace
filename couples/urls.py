from django.urls import path
from .views import GenerateCodeView, LinkPartnerView

urlpatterns = [
    path("generate-code", GenerateCodeView.as_view()),
    path("link",          LinkPartnerView.as_view()),
]
