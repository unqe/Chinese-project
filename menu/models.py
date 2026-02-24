"""
Menu app models — Category and MenuItem.
Translation fields (name_en, name_zh_hans etc.) are added automatically
by django-modeltranslation via translation.py registered in this app.
"""

from django.db import models


class Category(models.Model):
    """
    A menu section such as Starters, Mains, Noodles, Rice, Sides, Drinks.
    The 'order' field controls the display sequence on the menu page.
    """

    name = models.CharField(max_length=100)
    description = models.TextField(blank=True)
    order = models.PositiveIntegerField(default=0, help_text="Lower numbers appear first.")
    icon = models.CharField(
        max_length=50, blank=True,
        help_text="FontAwesome class e.g. fas fa-bowl-food"
    )

    class Meta:
        verbose_name_plural = "Categories"
        ordering = ["order", "name"]

    def __str__(self):
        return self.name


class MenuItem(models.Model):
    """
    A single dish on the menu, belonging to a Category.
    Items can be marked unavailable without being deleted, which keeps
    order history accurate. Spice level renders as chilli icons on the
    menu card.
    """

    SPICE_NONE = 0
    SPICE_MILD = 1
    SPICE_MEDIUM = 2
    SPICE_HOT = 3

    SPICE_CHOICES = [
        (SPICE_NONE, "No spice"),
        (SPICE_MILD, "Mild"),
        (SPICE_MEDIUM, "Medium"),
        (SPICE_HOT, "Hot"),
    ]

    category = models.ForeignKey(
        Category, on_delete=models.CASCADE, related_name="items"
    )
    name = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    price = models.DecimalField(max_digits=6, decimal_places=2)
    image = models.ImageField(upload_to="menu/", blank=True, null=True)
    spice_level = models.IntegerField(choices=SPICE_CHOICES, default=SPICE_NONE)
    is_vegetarian = models.BooleanField(default=False)
    is_vegan = models.BooleanField(default=False)
    is_available = models.BooleanField(default=True)
    is_popular = models.BooleanField(
        default=False, help_text="Marks item as a highlighted/popular dish."
    )
    allergens = models.CharField(
        max_length=300, blank=True,
        help_text="Comma-separated allergens e.g. gluten, nuts, dairy"
    )
    order = models.PositiveIntegerField(default=0, help_text="Display order within category.")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["order", "name"]

    def __str__(self):
        return f"{self.name} \u2014 \u00a3{self.price}"

    @property
    def spice_icons(self):
        """Returns a range used by templates to render chilli icons."""
        return range(self.spice_level)

