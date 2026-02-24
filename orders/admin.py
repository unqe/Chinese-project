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
    readonly_fields = ("item_name", "item_price", "quantity", "line_total", "notes")
    can_delete = False
    fields = ("item_name", "item_price", "quantity", "line_total", "notes")


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    # Use a single-page layout instead of tabs
    jazzmin_changeform_format = "single"

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
    readonly_fields = (
        "reference", "customer_link",
        "subtotal", "delivery_charge", "total", "created_at",
        "full_name", "email", "phone",
        "address_line1", "address_line2", "city", "postcode",
        "payment_method", "card_last_four", "special_instructions",
    )
    inlines = [OrderItemInline]
    date_hierarchy = "created_at"
    ordering = ("-created_at",)
    fieldsets = (
        ("📋  Order", {
            "fields": (("reference", "status"), "created_at"),
        }),
        ("👤  Customer", {
            "fields": ("customer_link", "user", ("full_name", "email"), "phone"),
        }),
        ("🚚  Delivery / Collection", {
            "fields": ("delivery_type", ("address_line1", "address_line2"), ("city", "postcode")),
        }),
        ("💳  Payment", {
            "fields": (("payment_method", "card_last_four"), ("subtotal", "delivery_charge", "total")),
        }),
        ("📝  Special Instructions", {
            "fields": ("special_instructions",),
            "classes": ("collapse",),
            "description": "Extra notes left by the customer at checkout.",
        }),
    )

    @admin.display(description="Account link")
    def customer_link(self, obj):
        if obj.user:
            url = reverse("admin:auth_user_change", args=[obj.user.pk])
            return format_html('<a href="{}">{}</a>', url, obj.user.email or obj.user.username)
        return format_html('<span style="color:#999">Guest</span>')

    def has_add_permission(self, request):
        # Orders are created by customers via the website, not manually in admin
        return False


@admin.register(OpeningHours)
class OpeningHoursAdmin(admin.ModelAdmin):
    list_display = ("day", "opening_time", "closing_time", "is_closed")
    list_editable = ("opening_time", "closing_time", "is_closed")
    ordering = ("day",)

