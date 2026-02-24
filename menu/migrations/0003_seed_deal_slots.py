"""
Data migration — seeds DealSlot rows for the four set-menu deals
that require customer item selection.

Deal PKs (confirmed from DB):
  45 – Deal for 2         : 2 starters + 2 mains + 2 egg fried rice
  46 – Family Feast (4)   : 4 mains + 4 rice/noodles (duck/rice fixed)
  47 – Student Special    : 1 starter + 1 main + 1 rice
  49 – Duck Banquet for 2 : 1 main each (2 people)

Category PKs:
   1 Starters   3 Duck   4 Chicken   5 Beef & Lamb
   6 Pork       7 Seafood  8 Vegetables
   9 Noodles   10 Fried Rice   11 Sides
"""

from django.db import migrations


# Helper: (label, order, [category_pks])
DEAL_SLOTS = {
    45: [  # Deal for 2
        ("Starter 1",      1, [1]),
        ("Starter 2",      2, [1]),
        ("Main Course 1",  3, [3, 4, 5, 6, 7, 8]),
        ("Main Course 2",  4, [3, 4, 5, 6, 7, 8]),
    ],
    46: [  # Family Feast (4 People)
        ("Main Course 1",    1, [3, 4, 5, 6, 7, 8]),
        ("Main Course 2",    2, [3, 4, 5, 6, 7, 8]),
        ("Main Course 3",    3, [3, 4, 5, 6, 7, 8]),
        ("Main Course 4",    4, [3, 4, 5, 6, 7, 8]),
        ("Rice / Noodles 1", 5, [9, 10, 11]),
        ("Rice / Noodles 2", 6, [9, 10, 11]),
        ("Rice / Noodles 3", 7, [9, 10, 11]),
        ("Rice / Noodles 4", 8, [9, 10, 11]),
    ],
    47: [  # Student Special
        ("Starter",          1, [1]),
        ("Main Course",      2, [3, 4, 5, 6, 7, 8]),
        ("Rice",             3, [10, 11]),  # Fried Rice or Sides (boiled rice)
    ],
    49: [  # Duck Banquet for 2
        ("Main Course 1",    1, [3, 4, 5, 6, 7, 8]),
        ("Main Course 2",    2, [3, 4, 5, 6, 7, 8]),
    ],
}


def seed_slots(apps, schema_editor):
    MenuItem = apps.get_model("menu", "MenuItem")
    Category = apps.get_model("menu", "Category")
    DealSlot = apps.get_model("menu", "DealSlot")

    for deal_pk, slots in DEAL_SLOTS.items():
        try:
            deal = MenuItem.objects.get(pk=deal_pk)
        except MenuItem.DoesNotExist:
            continue  # Skip if deal doesn't exist in this environment
        for label, order, cat_pks in slots:
            slot = DealSlot.objects.create(deal=deal, label=label, order=order)
            cats = Category.objects.filter(pk__in=cat_pks)
            slot.categories.set(cats)


def unseed_slots(apps, schema_editor):
    DealSlot = apps.get_model("menu", "DealSlot")
    DealSlot.objects.filter(deal_id__in=DEAL_SLOTS.keys()).delete()


class Migration(migrations.Migration):

    dependencies = [
        ("menu", "0002_deal_slot"),
    ]

    operations = [
        migrations.RunPython(seed_slots, reverse_code=unseed_slots),
    ]
