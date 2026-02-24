"""
Homepage route — lives in the menu app but serves the root URL (/).
Split into a separate file so it can be included without a prefix
in the main urls.py.
"""

from django.urls import path
from . import views

urlpatterns = [
    path("", views.homepage, name="home"),
]
