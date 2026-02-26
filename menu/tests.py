"""
Unit tests for the menu app.
Covers Category model, MenuItem model (including properties),
DealSlot.get_choices(), and the public menu page view.
"""

from decimal import Decimal
from django.test import TestCase

from menu.models import Category, MenuItem, DealSlot


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def make_category(name="Starters", order=1):
    return Category.objects.create(name=name, order=order)


def make_item(category, name="Spring Roll", price="4.50", available=True):
    return MenuItem.objects.create(
        category=category,
        name=name,
        price=Decimal(price),
        is_available=available,
    )


# ---------------------------------------------------------------------------
# Category model
# ---------------------------------------------------------------------------

class CategoryModelTest(TestCase):
    def test_str_returns_name(self):
        cat = Category(name="Soups")
        self.assertEqual(str(cat), "Soups")

    def test_ordering_by_order_field(self):
        cat_b = make_category(name="Mains", order=2)
        cat_a = make_category(name="Starters", order=1)
        cats = list(Category.objects.all())
        self.assertEqual(cats[0], cat_a)
        self.assertEqual(cats[1], cat_b)

    def test_created_without_icon(self):
        cat = Category.objects.create(name="Desserts")
        self.assertEqual(cat.icon, "")


# ---------------------------------------------------------------------------
# MenuItem model
# ---------------------------------------------------------------------------

class MenuItemModelTest(TestCase):
    def setUp(self):
        self.cat = make_category()

    def test_str_includes_name_and_price(self):
        item = MenuItem(name="Wontons", price=Decimal("5.50"))
        self.assertIn("Wontons", str(item))
        self.assertIn("5.50", str(item))

    def test_default_is_available_true(self):
        item = make_item(self.cat, name="Fried Rice")
        self.assertTrue(item.is_available)

    def test_default_spice_level_none(self):
        item = make_item(self.cat, name="Plain Noodles")
        self.assertEqual(item.spice_level, MenuItem.SPICE_NONE)

    def test_is_vegetarian_defaults_false(self):
        item = make_item(self.cat)
        self.assertFalse(item.is_vegetarian)

    def test_is_vegan_defaults_false(self):
        item = make_item(self.cat)
        self.assertFalse(item.is_vegan)


# ---------------------------------------------------------------------------
# MenuItem.spice_icons property
# ---------------------------------------------------------------------------

class SpiceIconsTest(TestCase):
    def setUp(self):
        self.cat = make_category()

    def test_no_spice_empty_range(self):
        item = make_item(self.cat)
        item.spice_level = MenuItem.SPICE_NONE
        self.assertEqual(len(list(item.spice_icons)), 0)

    def test_mild_one_icon(self):
        item = make_item(self.cat)
        item.spice_level = MenuItem.SPICE_MILD
        self.assertEqual(len(list(item.spice_icons)), 1)

    def test_medium_two_icons(self):
        item = make_item(self.cat)
        item.spice_level = MenuItem.SPICE_MEDIUM
        self.assertEqual(len(list(item.spice_icons)), 2)

    def test_hot_three_icons(self):
        item = make_item(self.cat)
        item.spice_level = MenuItem.SPICE_HOT
        self.assertEqual(len(list(item.spice_icons)), 3)


# ---------------------------------------------------------------------------
# DealSlot.get_choices()
# ---------------------------------------------------------------------------

class DealSlotGetChoicesTest(TestCase):
    def setUp(self):
        self.starters = make_category(name="Starters", order=1)
        self.mains = make_category(name="Mains", order=2)
        self.deal_cat = make_category(name="Deals & Set Menus", order=99)
        self.deal_item = make_item(self.deal_cat, name="Meal for 2", price="22.00")
        self.starter1 = make_item(self.starters, name="Spring Roll", price="4.00")
        self.starter2 = make_item(self.starters, name="Prawn Toast", price="5.00")
        self.main1 = make_item(self.mains, name="Chow Mein", price="8.00")
        self.unavail = make_item(self.starters, name="Sold Out", price="3.00", available=False)

    def test_get_choices_excludes_unavailable(self):
        slot = DealSlot.objects.create(deal=self.deal_item, label="Starter")
        slot.categories.set([self.starters])
        items = list(slot.get_choices())
        self.assertNotIn(self.unavail, items)

    def test_get_choices_filtered_by_category(self):
        slot = DealSlot.objects.create(deal=self.deal_item, label="Starter")
        slot.categories.set([self.starters])
        items = list(slot.get_choices())
        for item in items:
            self.assertEqual(item.category, self.starters)

    def test_get_choices_excludes_deal_items(self):
        slot = DealSlot.objects.create(deal=self.deal_item, label="Any")
        # no category restriction — should still exclude deal category items
        items = list(slot.get_choices())
        self.assertNotIn(self.deal_item, items)

    def test_get_choices_no_category_returns_all_available(self):
        slot = DealSlot.objects.create(deal=self.deal_item, label="Free choice")
        # No categories set → all available items (except deals category)
        items = list(slot.get_choices())
        self.assertIn(self.starter1, items)
        self.assertIn(self.main1, items)


# ---------------------------------------------------------------------------
# Menu page view
# ---------------------------------------------------------------------------

class MenuPageViewTest(TestCase):
    def setUp(self):
        self.cat = make_category(name="Noodles")
        self.item = make_item(self.cat, name="Beef Noodles", price="9.00")
        self.unavail = make_item(self.cat, name="Unavailable Dish", price="7.00", available=False)

    def test_menu_page_loads(self):
        response = self.client.get("/menu/")
        self.assertEqual(response.status_code, 200)

    def test_available_item_shown(self):
        response = self.client.get("/menu/")
        self.assertContains(response, "Beef Noodles")

    def test_unavailable_item_still_rendered(self):
        # Unavailable items show as sold out, not hidden
        response = self.client.get("/menu/")
        self.assertContains(response, "Unavailable Dish")

    def test_category_heading_shown(self):
        response = self.client.get("/menu/")
        self.assertContains(response, "Noodles")
