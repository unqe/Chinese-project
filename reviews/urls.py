"""
URL routes for the reviews app — /reviews/
"""

from django.urls import path
from . import views

app_name = "reviews"

urlpatterns = [
    path("", views.reviews_list, name="list"),
    path("add/<str:order_reference>/", views.add_review, name="add"),
    path("by-receipt/", views.guest_review, name="guest_review"),
    path("edit/<int:pk>/", views.edit_review, name="edit"),
    path("delete/<int:pk>/", views.delete_review, name="delete"),
]
