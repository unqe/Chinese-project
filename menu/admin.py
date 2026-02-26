"""
Menu app admin configuration.
Uses tabular inlines so category items can be managed on the category page.
"""

from django.contrib import admin
from django.db.models import Count
from django.utils.html import format_html
from modeltranslation.admin import TranslationAdmin, TranslationTabularInline
from .models import Category, MenuItem, DealSlot


class MenuItemInline(TranslationTabularInline):
    """Shows menu items inline when editing a Category."""
    model = MenuItem
    extra = 1
    fields = ("name", "price", "spice_level", "is_available", "is_popular", "order")


class DealSlotInline(admin.TabularInline):
    """Configure picker slots for a set-menu deal item."""
    model = DealSlot
    extra = 2
    fields = ("label", "categories", "order")
    filter_horizontal = ("categories",)


@admin.register(Category)
class CategoryAdmin(TranslationAdmin):
    list_display = ("name", "order", "icon")
    list_editable = ("order",)
    search_fields = ("name",)
    inlines = [MenuItemInline]


@admin.register(MenuItem)
class MenuItemAdmin(TranslationAdmin):
    list_display = (
        "image_thumb",
        "name",
        "category",
        "price",
        "spice_level",
        "is_available",
        "is_popular",
        "is_vegetarian",
        "times_ordered",
    )
    list_filter = ("category", "is_available", "is_popular", "spice_level", "is_vegetarian")
    list_editable = ("price", "is_available", "is_popular")
    search_fields = ("name", "description")
    ordering = ("category", "order", "name")
    readonly_fields = ("image_preview", "times_ordered")
    inlines = [DealSlotInline]
    fieldsets = (
        (
            "🍜 Item Details",
            {
                "fields": ("category", "name", "description", "price", "order"),
            },
        ),
        (
            "🖼️ Image",
            {
                "fields": ("image_preview", "image"),
                "description": (
                    "Upload a food photo — stored via Cloudinary. "
                    "Recommended size: <strong>800×600px</strong> or square. "
                    "JPEG/WebP preferred for performance."
                ),
            },
        ),
        (
            "🌶️ Dietary & Attributes",
            {
                "fields": (
                    "spice_level",
                    "is_vegetarian",
                    "is_vegan",
                    "allergens",
                    "is_popular",
                    "is_available",
                ),
            },
        ),
    )

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        return qs.annotate(_times_ordered=Count("order_items"))

    @admin.display(description="", ordering="name")
    def image_thumb(self, obj):
        """Small thumbnail shown in the list view."""
        if obj.image:
            try:
                url = obj.image.url
            except Exception:
                return format_html('<span style="color:#555;font-size:.75rem;">No URL</span>')
            return format_html(
                '<img src="{}" style="width:46px;height:46px;object-fit:cover;'
                'border-radius:6px;border:1px solid rgba(212,160,23,.25);" alt="{}">',
                url,
                obj.name,
            )
        return format_html(
            '<div style="width:46px;height:46px;border-radius:6px;background:#1c1008;'
            'border:1px dashed rgba(212,160,23,.2);display:flex;align-items:center;'
            'justify-content:center;color:#9a8870;font-size:1.1rem;">🍽</div>'
        )

    @admin.display(description="Image Preview")
    def image_preview(self, obj):
        """Large preview shown on the change form."""
        if obj.image:
            try:
                url = obj.image.url
            except Exception:
                return format_html('<p style="color:#9a8870;font-size:.85rem;">Image URL unavailable.</p>')
            return format_html(
                '<div style="margin:.5rem 0;">'
                '<img src="{}" alt="{}" style="max-width:320px;max-height:260px;'
                'object-fit:cover;border-radius:10px;border:1px solid rgba(212,160,23,.3);'
                'box-shadow:0 4px 16px rgba(0,0,0,.4);">'
                '<p style="color:#9a8870;font-size:.75rem;margin:.4rem 0 0;">'
                'Current image — upload a new file below to replace it.</p>'
                '</div>',
                url,
                obj.name,
            )
        return format_html(
            '<div style="padding:.75rem 1rem;background:rgba(212,160,23,.06);border:1px dashed '
            'rgba(212,160,23,.25);border-radius:8px;color:#9a8870;font-size:.85rem;">'
            '<i class="fas fa-image me-2" style="color:#d4a017;"></i>'
            'No image uploaded yet — use the field below to add one.'
            '</div>'
        )

    @admin.display(description="Times ordered", ordering="_times_ordered")
    def times_ordered(self, obj):
        return getattr(obj, "_times_ordered", "—")

