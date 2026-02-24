"""
django-modeltranslation registration for the menu app.
This tells modeltranslation to create additional database columns for each
registered field in each language (e.g. name_en, name_zh_hans, description_en,
description_zh_hans). The base field (name, description) acts as the fallback.
"""

from modeltranslation.translator import register, TranslationOptions
from .models import Category, MenuItem


@register(Category)
class CategoryTranslationOptions(TranslationOptions):
    fields = ("name", "description")


@register(MenuItem)
class MenuItemTranslationOptions(TranslationOptions):
    fields = ("name", "description")
