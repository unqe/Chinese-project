"""
Custom template filters for the menu app.
"""

from django import template

register = template.Library()


@register.filter
def split_allergens(value):
    """Split a comma-separated allergens string into a list of stripped strings."""
    if not value:
        return []
    return [a.strip() for a in value.split(",") if a.strip()]
