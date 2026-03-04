from django.contrib.auth import get_user_model
from django.urls import path

from src.users.views import owners

Users = get_user_model()
app_name = "users"

urlpatterns = [
    path("admin/owners/", owners.OwnersView.as_view(), name="owners"),
]
