"""
URL routes for the menu app — /menu/
"""

from django.urls import path
from . import views

app_name = "menu"

urlpatterns = [
    path("", views.menu_page, name="menu"),
    path("item/<int:pk>/", views.item_detail, name="item_detail"),
    path("staff/update-image/<int:pk>/", views.staff_update_image, name="staff_update_image"),
]
