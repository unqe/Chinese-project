"""
Menu app admin configuration.
Uses tabular inlines so category items can be managed on the category page.
"""

from django.contrib import admin
from django.db.models import Count
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
        "name", "category", "price", "spice_level",
        "is_available", "is_popular", "is_vegetarian", "times_ordered",
    )
    list_filter = ("category", "is_available", "is_popular", "spice_level", "is_vegetarian")
    list_editable = ("price", "is_available", "is_popular")
    search_fields = ("name", "description")
    ordering = ("category", "order", "name")
    inlines = [DealSlotInline]

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        return qs.annotate(_times_ordered=Count("order_items"))

    @admin.display(description="Times ordered", ordering="_times_ordered")
    def times_ordered(self, obj):
        return obj._times_ordered

