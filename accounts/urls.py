"""
URL routes for the accounts app — /profile/
"""

from django.urls import path
from . import views

app_name = "accounts"

urlpatterns = [
    path("", views.profile, name="profile"),
]
