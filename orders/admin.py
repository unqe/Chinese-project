"""
Orders app admin configuration.
Order items are shown inline on the Order page so the full order is
visible at a glance. Status can be changed directly from the list view.
"""

from django.contrib import admin
from django.utils.html import format_html
from django.urls import reverse
from .models import Order, OrderItem, OpeningHours


class OrderItemInline(admin.TabularInline):
    """Displays all items for an order inline on the order detail page."""
    model = OrderItem
    extra = 0
    readonly_fields = ("item_name", "item_price", "quantity", "line_total")
    can_delete = False


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = (
        "reference", "full_name", "customer_link", "delivery_type",
        "payment_method", "total", "status", "created_at"
    )
    list_filter = ("status", "delivery_type", "payment_method", "created_at", "user")
    list_editable = ("status",)
    search_fields = (
        "reference", "full_name", "email", "phone",
        "user__email", "user__username",
    )
    readonly_fields = ("reference", "subtotal", "delivery_charge", "total", "created_at")
    inlines = [OrderItemInline]
    date_hierarchy = "created_at"
    ordering = ("-created_at",)

    @admin.display(description="Account")
    def customer_link(self, obj):
        if obj.user:
            url = reverse("admin:auth_user_change", args=[obj.user.pk])
            return format_html('<a href="{}">{}</a>', url, obj.user.email or obj.user.username)
        return format_html('<span style="color:#999">Guest</span>')


@admin.register(OpeningHours)
class OpeningHoursAdmin(admin.ModelAdmin):
    list_display = ("day", "opening_time", "closing_time", "is_closed")
    list_editable = ("opening_time", "closing_time", "is_closed")
    ordering = ("day",)

