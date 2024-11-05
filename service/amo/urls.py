from django.urls import path
from .views import AmoGetFieldIdView


urlpatterns = [
    path("field", AmoGetFieldIdView.as_view())
]