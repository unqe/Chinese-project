"""
Menu app views — homepage and full menu page.
"""

from django.shortcuts import render, get_object_or_404
from .models import Category, MenuItem
from orders.models import OpeningHours
from orders.basket import Basket
import datetime
from zoneinfo import ZoneInfo

LONDON_TZ = ZoneInfo("Europe/London")


def homepage(request):
    """
    Main landing page. Shows popular dishes, opening hours today,
    and a hero section with a call-to-action to order.
    Open/closed status is based on real London time (handles BST/GMT).
    """
    popular_items = MenuItem.objects.filter(
        is_popular=True, is_available=True
    ).select_related("category")[:8]

    opening_hours = OpeningHours.objects.all()

    # Use London local time so BST/GMT is handled automatically
    now_london = datetime.datetime.now(tz=LONDON_TZ)
    today = now_london.weekday()   # 0=Monday, 6=Sunday
    now_time = now_london.time()

    is_open = False
    today_hours = None
    for hours in opening_hours:
        if hours.day == today:
            today_hours = hours
            if not hours.is_closed and hours.opening_time and hours.closing_time:
                is_open = hours.opening_time <= now_time <= hours.closing_time
            break

    context = {
        "popular_items": popular_items,
        "opening_hours": opening_hours,
        "is_open": is_open,
        "today_hours": today_hours,
    }
    return render(request, "home.html", context)


def menu_page(request):
    """
    Full menu page grouped by category.
    Only shows available items and supports a 'category' query param
    to scroll/highlight a specific section.
    Passes basket quantities so cards can show +/- controls.
    """
    categories = Category.objects.prefetch_related("items").all()

    filtered_categories = []
    for cat in categories:
        available_items = cat.items.filter(is_available=True)
        if available_items.exists():
            filtered_categories.append((cat, available_items))

    active_category = request.GET.get("category", None)

    # Build a dict of {item_id: quantity} from the current basket
    basket = Basket(request)
    basket_quantities = {int(k): v["quantity"] for k, v in basket.basket.items()}
    basket_count = basket.get_total_quantity()
    basket_subtotal = basket.get_subtotal()

    return render(request, "menu/menu.html", {
        "categories": filtered_categories,
        "active_category": active_category,
        "basket_quantities": basket_quantities,
        "basket_count": basket_count,
        "basket_subtotal": basket_subtotal,
    })


def item_detail(request, pk):
    """
    Detail page for a single menu item. Shows full description,
    allergens, spice level, and an add-to-basket button.
    """
    item = get_object_or_404(MenuItem, pk=pk, is_available=True)
    related_items = MenuItem.objects.filter(
        category=item.category, is_available=True
    ).exclude(pk=pk)[:4]

    return render(request, "menu/item_detail.html", {
        "item": item,
        "related_items": related_items,
    })

