from django.urls import path

# Create your views here.
from src.core import views

app_name = "core"
urlpatterns = [
    path("home/", views.home, name="home"),
]
