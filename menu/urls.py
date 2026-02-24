"""
URL routes for the menu app — /menu/
"""

from django.urls import path
from . import views

app_name = "menu"

urlpatterns = [
    path("", views.menu_page, name="menu"),
    path("item/<int:pk>/", views.item_detail, name="item_detail"),
]
