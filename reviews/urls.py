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
    path("from-order/<str:reference>/", views.guest_review_prefill, name="guest_review_prefill"),
    path("edit/<int:pk>/", views.edit_review, name="edit"),
    path("delete/<int:pk>/", views.delete_review, name="delete"),
    path("reply/<int:pk>/", views.reply_review, name="reply"),
    path("reply/<int:pk>/delete/", views.delete_reply, name="delete_reply"),
    path("staff-delete/<int:pk>/", views.staff_delete_review, name="staff_delete"),
]
