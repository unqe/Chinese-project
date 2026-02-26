"""
Menu app views — homepage and full menu page.
"""

from django.shortcuts import render, get_object_or_404
from django.db.models import Count
from django.http import JsonResponse
from django.contrib.admin.views.decorators import staff_member_required
from django.views.decorators.http import require_POST
from .models import Category, MenuItem, DealSlot
from orders.models import OpeningHours, OrderItem
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
        all_items = cat.items.all()
        # Show section only if at least one item is available;
        # unavailable items are included so they display with a "Sold Out" badge.
        if all_items.filter(is_available=True).exists():
            filtered_categories.append((cat, all_items))

    active_category = request.GET.get("category", None)

    # Build a dict of {item_id: quantity} from the current basket
    basket = Basket(request)
    basket_quantities = {int(k): v["quantity"] for k, v in basket.basket.items()}
    basket_count = basket.get_total_quantity()
    basket_subtotal = basket.get_subtotal()

    # PKs of deal items that have at least one choosable slot
    deal_item_pks = set(
        DealSlot.objects.values_list("deal_id", flat=True).distinct()
    )

    # Favourite items for logged-in users — top 6 most-ordered available items
    favourite_items = []
    if request.user.is_authenticated:
        fav_ids = (
            OrderItem.objects
            .filter(order__user=request.user, menu_item__is_available=True)
            .values("menu_item_id")
            .annotate(cnt=Count("id"))
            .order_by("-cnt")[:6]
            .values_list("menu_item_id", flat=True)
        )
        if fav_ids:
            # Preserve ordering by count
            fav_map = {pk: i for i, pk in enumerate(fav_ids)}
            qs = MenuItem.objects.filter(pk__in=fav_ids).select_related("category")
            favourite_items = sorted(qs, key=lambda m: fav_map.get(m.pk, 99))

    return render(request, "menu/menu.html", {
        "categories": filtered_categories,
        "active_category": active_category,
        "basket_quantities": basket_quantities,
        "basket_count": basket_count,
        "basket_subtotal": basket_subtotal,
        "deal_item_pks": deal_item_pks,
        "favourite_items": favourite_items,
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
    is_deal = DealSlot.objects.filter(deal=item).exists()

    return render(request, "menu/item_detail.html", {
        "item": item,
        "related_items": related_items,
        "is_deal": is_deal,
    })


@staff_member_required
@require_POST
def staff_update_image(request, pk):
    """
    Staff-only AJAX endpoint to update or remove a MenuItem image.
    POST: multipart form with 'image' file, or 'remove_image'=1 to clear.
    Returns JSON {ok, image_url}.
    """
    item = get_object_or_404(MenuItem, pk=pk)
    if request.POST.get("remove_image") == "1":
        item.image.delete(save=True)
        return JsonResponse({"ok": True, "image_url": ""})
    if "image" in request.FILES:
        item.image = request.FILES["image"]
        item.save(update_fields=["image"])
        try:
            url = item.image.url
        except Exception:
            url = ""
        return JsonResponse({"ok": True, "image_url": url})
    return JsonResponse({"ok": False, "error": "No file uploaded."}, status=400)


@staff_member_required
@require_POST
def staff_toggle_availability(request, pk):
    """Toggle a menu item's is_available flag (sold out ↔ available) via AJAX."""
    item = get_object_or_404(MenuItem, pk=pk)
    item.is_available = not item.is_available
    item.save(update_fields=["is_available"])
    return JsonResponse({"ok": True, "is_available": item.is_available, "pk": item.pk})

