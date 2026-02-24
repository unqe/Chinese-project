"""
URL routes for the orders app — /orders/
"""

from django.urls import path
from . import views

app_name = "orders"

urlpatterns = [
    path("basket/", views.basket_view, name="basket"),
    path("basket/add/<int:item_id>/", views.basket_add, name="basket_add"),
    path("basket/update/<int:item_id>/", views.basket_update, name="basket_update"),
    path("basket/remove/<int:item_id>/", views.basket_remove, name="basket_remove"),
    path("basket/note/<int:item_id>/", views.basket_note, name="basket_note"),
    path("checkout/", views.checkout, name="checkout"),
    path("confirmation/<str:reference>/", views.order_confirmation, name="confirmation"),
    path("history/", views.order_history, name="history"),
    path("detail/<str:reference>/", views.order_detail, name="order_detail"),
    path("reorder/<str:reference>/", views.reorder, name="reorder"),
    path("status/<str:reference>/", views.order_status_api, name="order_status_api"),
    path("deal-picker/<int:item_id>/", views.deal_picker, name="deal_picker"),
]
