"""
Orders app views — basket, checkout, confirmation, and order history.
"""

import datetime
from zoneinfo import ZoneInfo
from decimal import Decimal

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib.admin.views.decorators import staff_member_required
from django.contrib.auth import get_user_model
from django.contrib import messages
from django.contrib.admin.models import LogEntry, ADDITION
from django.contrib.contenttypes.models import ContentType
from django.db.models import F
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from django.utils import timezone
from datetime import timedelta
from django.core.cache import cache

from .basket import Basket, MIN_ORDER_DELIVERY, FREE_DELIVERY_THRESHOLD, DELIVERY_CHARGE
from .forms import CheckoutForm
from .models import Order, OrderItem, OpeningHours, PromoCode
from menu.models import MenuItem, DealSlot


def _log_admin_action(request, obj, action_flag, message=""):
    """Create a Django admin LogEntry so the action shows in Recent Actions."""
    User = get_user_model()
    if request.user.is_authenticated:
        actor_id = request.user.pk
    else:
        actor_id = User.objects.filter(is_superuser=True).values_list("pk", flat=True).first()
    if actor_id is None:
        return
    LogEntry.objects.log_action(
        user_id=actor_id,
        content_type_id=ContentType.objects.get_for_model(obj).pk,
        object_id=obj.pk,
        object_repr=str(obj),
        action_flag=action_flag,
        change_message=message,
    )


def _check_rate_limit(request, key, limit=10, period=60):
    """
    Returns True if the request should proceed, False if it should be blocked.
    Tracks attempts per remote IP using Django's cache backend.
    """
    ip = (
        request.META.get("HTTP_X_FORWARDED_FOR", "").split(",")[0].strip()
        or request.META.get("REMOTE_ADDR", "anon")
    )
    cache_key = f"rl:{key}:{ip}"
    count = cache.get(cache_key, 0)
    if count >= limit:
        return False
    if count == 0:
        cache.set(cache_key, 1, period)
    else:
        try:
            cache.incr(cache_key)
        except Exception:
            cache.set(cache_key, count + 1, period)
    return True


LONDON_TZ = ZoneInfo("Europe/London")


def _revalidate_promo(basket, request=None):
    """
    After any basket mutation, check whether the applied promo code still meets
    its minimum-order requirement against the new subtotal. If it no longer
    qualifies, remove it from the session and optionally warn the user.
    Returns True if the promo was removed, False otherwise.
    """
    code = basket.promo_code
    if not code:
        return False
    try:
        promo = PromoCode.objects.get(code=code)
    except PromoCode.DoesNotExist:
        basket.remove_promo()
        return True
    valid, err = promo.is_valid(subtotal=basket.get_subtotal())
    if not valid:
        basket.remove_promo()
        if request is not None:
            messages.warning(
                request,
                f"Promo code {code} has been removed — your basket no longer meets the minimum required.",
            )
        return True
    return False


def _basket_ajax_summary(basket, item_id=None):
    """Build a rich JSON-serialisable dict with all basket summary data for AJAX responses."""
    subtotal = basket.get_subtotal()
    delivery_charge = basket.get_delivery_charge()  # defaults to 'delivery' type
    discount = basket.get_discount()
    total = basket.get_total()
    free_del_remaining = max(Decimal("0.00"), FREE_DELIVERY_THRESHOLD - subtotal)
    free_del_pct = min(100, int(subtotal / FREE_DELIVERY_THRESHOLD * 100)) if subtotal > 0 else 0
    result = {
        "subtotal": str(subtotal),
        "delivery_charge": str(delivery_charge),
        "delivery_is_free": delivery_charge == Decimal("0.00"),
        "discount": str(discount),
        "has_discount": discount > Decimal("0.00"),
        "total": str(total),
        "free_delivery_remaining": str(free_del_remaining),
        "free_delivery_pct": free_del_pct,
        "promo_code": basket.promo_code,
        # Legacy keys kept for compatibility with menu-page AJAX JS
        "basket_count": basket.get_total_quantity(),
        "basket_subtotal": str(subtotal),
    }
    if item_id is not None:
        item_data = basket.basket.get(str(item_id), {})
        qty = item_data.get("quantity", 0)
        price = Decimal(item_data.get("price", "0")) if item_data else Decimal("0")
        result["item_quantity"] = qty
        result["item_line_total"] = str(price * qty)
    return result


# PKs for upsell items (kept as constants so they're easy to change in admin)
_PRAWN_CRACKERS_PK = 36
_COKE_PK = 43
_FREE_DRINK_THRESHOLD = Decimal("70.00")


def _get_opening_status():
    """
    Return (is_open: bool, next_open_text: str | None) based on London time.
    next_open_text is a human-readable string like "Tomorrow at 12:00 PM"
    or "Saturday at 5:00 PM".
    """
    now_london = datetime.datetime.now(tz=LONDON_TZ)
    today = now_london.weekday()  # 0=Monday
    now_time = now_london.time()

    hours_by_day = {h.day: h for h in OpeningHours.objects.all()}

    today_hours = hours_by_day.get(today)
    is_open = False
    if today_hours and not today_hours.is_closed and today_hours.opening_time and today_hours.closing_time:
        is_open = today_hours.opening_time <= now_time <= today_hours.closing_time

    # Find next opening window (within 7 days)
    next_open_text = None
    for offset in range(1, 8):
        check_day = (today + offset) % 7
        h = hours_by_day.get(check_day)
        if h and not h.is_closed and h.opening_time:
            # If same day but before opening, that counts as "today later"
            if offset == 0 and now_time < h.opening_time:
                day_label = "Today"
            elif offset == 1:
                day_label = "Tomorrow"
            else:
                day_label = h.get_day_display()
            open_str = datetime.datetime.combine(datetime.date.today(), h.opening_time).strftime("%-I:%M %p")
            next_open_text = f"{day_label} at {open_str}"
            break
    # Also check if today opens later
    if not is_open and today_hours and not today_hours.is_closed and today_hours.opening_time:
        if now_time < today_hours.opening_time:
            open_str = datetime.datetime.combine(datetime.date.today(), today_hours.opening_time).strftime("%-I:%M %p")
            next_open_text = f"Today at {open_str}"
    return is_open, next_open_text


# Minutes remaining from *now* for each delivery type + status combination
_STATUS_EST_MINUTES = {
    "delivery": {
        "pending": 45,
        "confirmed": 40,
        "preparing": 25,
        "out_for_delivery": 15,
        "completed": 0,
        "cancelled": 0,
    },
    "collection": {
        "pending": 15,
        "confirmed": 12,
        "preparing": 8,
        "ready": 5,
        "completed": 0,
        "cancelled": 0,
    },
}


def _est_for_status(order):
    """Return estimated remaining minutes based on current order status."""
    mode = "delivery" if order.is_delivery else "collection"
    return _STATUS_EST_MINUTES.get(mode, {}).get(order.status, 45 if order.is_delivery else 15)


def basket_view(request):
    """Displays the current basket contents."""
    basket = Basket(request)
    basket_item_ids = set(basket.basket.keys())

    # Category-based "Customers also ordered" upsell
    basket_cat_ids = set(
        MenuItem.objects.filter(pk__in=[int(k) for k in basket_item_ids])
        .values_list("category_id", flat=True)
    )
    if basket_cat_ids:
        popular_items = (
            MenuItem.objects
            .filter(is_available=True, category_id__in=basket_cat_ids)
            .exclude(pk__in=basket_item_ids)
            .order_by("-is_popular", "name")[:4]
        )
        if not popular_items.exists():
            popular_items = (
                MenuItem.objects
                .filter(is_popular=True, is_available=True)
                .exclude(pk__in=basket_item_ids)[:4]
            )
    else:
        popular_items = (
            MenuItem.objects
            .filter(is_popular=True, is_available=True)
            .exclude(pk__in=basket_item_ids)[:4]
        )

    subtotal = basket.get_subtotal()

    # Auto-apply first-order discount for new logged-in users
    if (
        request.user.is_authenticated
        and basket
        and not basket.promo_code
        and not request.session.get("_first_promo_applied")
        and not Order.objects.filter(user=request.user).exists()
    ):
        first_promo = PromoCode.objects.filter(first_order_only=True, active=True).first()
        if first_promo:
            valid, _ = first_promo.is_valid(subtotal=subtotal)
            if valid:
                discount = first_promo.get_discount(subtotal)
                basket.apply_promo(first_promo.code, discount)
                request.session["_first_promo_applied"] = True
                messages.success(
                    request,
                    f"\U0001f389 First order discount ({first_promo}) applied automatically!",
                )

    # Contextual upsell nudges
    show_prawn_crackers = str(_PRAWN_CRACKERS_PK) not in basket_item_ids
    show_free_drink = subtotal >= _FREE_DRINK_THRESHOLD
    prawn_crackers = None
    coke = None
    if show_prawn_crackers:
        try:
            prawn_crackers = MenuItem.objects.get(pk=_PRAWN_CRACKERS_PK, is_available=True)
        except MenuItem.DoesNotExist:
            show_prawn_crackers = False
    if show_free_drink:
        try:
            coke = MenuItem.objects.get(pk=_COKE_PK, is_available=True)
        except MenuItem.DoesNotExist:
            pass
    is_open, next_open_text = _get_opening_status()
    free_delivery_remaining = max(Decimal("0.00"), Decimal("20.00") - subtotal)
    return render(request, "orders/basket.html", {
        "basket": basket,
        "popular_items": popular_items,
        "show_prawn_crackers": show_prawn_crackers,
        "prawn_crackers": prawn_crackers,
        "show_free_drink": show_free_drink,
        "coke": coke,
        "min_order_delivery": MIN_ORDER_DELIVERY,
        "is_open": is_open,
        "next_open_text": next_open_text,
        "free_delivery_remaining": free_delivery_remaining,
    })


@require_POST
def basket_add(request, item_id):
    """
    Adds a menu item to the session basket.
    Returns JSON when called via AJAX, or redirects for plain forms.
    """
    basket = Basket(request)
    item = get_object_or_404(MenuItem, pk=item_id, is_available=True)
    quantity = int(request.POST.get("quantity", 1))
    basket.add(item, quantity=quantity)

    if request.headers.get("X-Requested-With") == "XMLHttpRequest":
        data = _basket_ajax_summary(basket, item_id)
        data["success"] = True
        data["message"] = f"{item.name} added to basket."
        return JsonResponse(data)

    messages.success(request, f"\u2713 {item.name} added to your basket.")
    if request.POST.get("from_basket"):
        return redirect("orders:basket")
    return redirect("menu:menu")


@require_POST
def basket_update(request, item_id):
    """Updates the quantity of a basket item. Supports AJAX."""
    basket = Basket(request)
    quantity = int(request.POST.get("quantity", 1))
    basket.update(item_id, quantity)
    promo_removed = _revalidate_promo(basket, request)

    if request.headers.get("X-Requested-With") == "XMLHttpRequest":
        data = _basket_ajax_summary(basket, item_id)
        data["success"] = True
        data["promo_removed"] = promo_removed
        return JsonResponse(data)
    return redirect("orders:basket")


@require_POST
def basket_note(request, item_id):
    """Saves a per-item note to the session basket. Called via AJAX."""
    basket = Basket(request)
    note = request.POST.get("note", "").strip()
    basket.set_notes(item_id, note)
    return JsonResponse({"success": True})


@require_POST
def basket_remove(request, item_id):
    """Removes an item from the basket entirely. Supports AJAX."""
    basket = Basket(request)
    basket.remove(item_id)
    promo_removed = _revalidate_promo(basket, request)

    if request.headers.get("X-Requested-With") == "XMLHttpRequest":
        data = _basket_ajax_summary(basket)
        data["success"] = True
        data["item_quantity"] = 0
        data["item_line_total"] = "0.00"
        data["promo_removed"] = promo_removed
        return JsonResponse(data)
    messages.warning(request, "Item removed from basket.")
    return redirect("orders:basket")


@require_POST
def apply_promo(request):
    """Validate and apply a promo code to the basket session."""
    basket = Basket(request)
    is_ajax = request.headers.get("X-Requested-With") == "XMLHttpRequest"
    if not _check_rate_limit(request, "apply_promo"):
        err = "Too many attempts. Please wait a minute and try again."
        if is_ajax:
            return JsonResponse({"success": False, "error": err}, status=429)
        messages.error(request, err)
        return redirect("orders:basket")
    code_str = request.POST.get("promo_code", "").strip().upper()
    if not code_str:
        if is_ajax:
            return JsonResponse({"success": False, "error": "Please enter a promo code."})
        messages.error(request, "Please enter a promo code.")
        return redirect("orders:basket")

    try:
        promo = PromoCode.objects.get(code__iexact=code_str)
    except PromoCode.DoesNotExist:
        if is_ajax:
            return JsonResponse({"success": False, "error": f"'{code_str}' is not a valid promo code."})
        messages.error(request, f"'{code_str}' is not a valid promo code.")
        return redirect("orders:basket")

    valid, err = promo.is_valid(subtotal=basket.get_subtotal())
    if not valid:
        if is_ajax:
            return JsonResponse({"success": False, "error": err})
        messages.error(request, err)
        return redirect("orders:basket")

    # First-order-only codes are restricted to users who have never placed an order
    if promo.first_order_only:
        fo_err = None
        if not request.user.is_authenticated:
            fo_err = "This promo code is for first-time customers only. Please sign in to use it."
        elif Order.objects.filter(user=request.user).exists():
            fo_err = "This promo code is for new customers only."
        if fo_err:
            if is_ajax:
                return JsonResponse({"success": False, "error": fo_err})
            messages.error(request, fo_err)
            return redirect("orders:basket")

    discount = promo.get_discount(basket.get_subtotal())
    basket.apply_promo(promo.code, discount)
    if is_ajax:
        data = _basket_ajax_summary(basket)
        data["success"] = True
        data["promo_code"] = promo.code
        data["message"] = f"Promo code {promo.code} applied — £{discount} off!"
        return JsonResponse(data)
    messages.success(request, f"Promo code {promo.code} applied — £{discount} off!")
    return redirect("orders:basket")


@require_POST
def remove_promo(request):
    """Remove any applied promo code from the basket session."""
    basket = Basket(request)
    basket.remove_promo()
    # Prevent auto-apply from re-applying a first-order code the user just removed
    request.session["_first_promo_applied"] = True
    if request.headers.get("X-Requested-With") == "XMLHttpRequest":
        data = _basket_ajax_summary(basket)
        data["success"] = True
        return JsonResponse(data)
    messages.info(request, "Promo code removed.")
    return redirect("orders:basket")


def checkout(request):
    """
    Checkout page. Pre-fills with saved profile data for logged-in users.
    Guests can also checkout — they just need to enter an email.
    Creates the Order and OrderItems on POST, then clears the basket.
    If the restaurant is currently closed, a pre-booking notice is shown.
    """
    basket = Basket(request)
    is_open, next_open_text = _get_opening_status()

    if not basket:
        messages.warning(request, "Your basket is empty.")
        return redirect("menu:menu")

    initial = {}
    if request.user.is_authenticated:
        profile = getattr(request.user, "profile", None)
        if profile:
            initial = {
                "full_name": request.user.get_full_name() or request.user.username,
                "email": request.user.email,
                "phone": profile.phone,
                "address_line1": profile.address_line1,
                "address_line2": profile.address_line2,
                "city": profile.city,
                "postcode": profile.postcode,
            }

    if request.method == "POST":
        if not _check_rate_limit(request, "checkout", limit=5, period=60):
            messages.error(request, "Too many checkout attempts. Please wait a minute and try again.")
            return redirect("orders:checkout")
        form = CheckoutForm(request.POST)
        if form.is_valid():
            delivery_type = form.cleaned_data["delivery_type"]
            # Enforce minimum order for delivery
            if delivery_type == "delivery" and basket.get_subtotal() < MIN_ORDER_DELIVERY:
                messages.error(
                    request,
                    f"A minimum order of £{MIN_ORDER_DELIVERY} is required for delivery. "
                    "There's no minimum for collection."
                )
                profile_has_address_err = False
                if request.user.is_authenticated:
                    _p = getattr(request.user, "profile", None)
                    profile_has_address_err = bool(_p and _p.address_line1)
                return render(request, "orders/checkout.html", {
                    "form": form,
                    "basket": basket,
                    "delivery_charge": basket.get_delivery_charge("delivery"),
                    "free_delivery_threshold": 20,
                    "min_order_delivery": MIN_ORDER_DELIVERY,
                    "is_open": is_open,
                    "next_open_text": next_open_text,
                    "profile_has_address": profile_has_address_err,
                })
            order = form.save(commit=False)
            order.user = request.user if request.user.is_authenticated else None
            order.subtotal = basket.get_subtotal()
            order.delivery_charge = basket.get_delivery_charge(delivery_type)
            # Final safety check: ensure the promo still qualifies at checkout subtotal
            _revalidate_promo(basket)
            order.discount_amount = basket.get_discount()
            order.promo_code = basket.promo_code
            order.total = basket.get_total(delivery_type)

            if form.cleaned_data.get("payment_method") == Order.PAYMENT_CARD:
                raw_card = form.cleaned_data.get("card_number", "").replace(" ", "")
                order.card_last_four = raw_card[-4:] if raw_card else ""

            order.save()

            # Increment promo code uses_count
            if order.promo_code:
                PromoCode.objects.filter(code=order.promo_code).update(
                    uses_count=F("uses_count") + 1
                )

            # Log to admin Recent Actions
            _log_admin_action(request, order, ADDITION, "Order placed via website")

            for item_data in basket:
                OrderItem.objects.create(
                    order=order,
                    menu_item=item_data["menu_item"],
                    item_name=item_data["menu_item"].name,
                    item_price=item_data["price"],
                    quantity=item_data["quantity"],
                    notes=item_data.get("notes", ""),
                )

            # Save address back to profile if checkbox ticked
            if request.user.is_authenticated and request.POST.get("save_address"):
                profile = getattr(request.user, "profile", None)
                if profile:
                    profile.address_line1 = form.cleaned_data.get("address_line1", "")
                    profile.address_line2 = form.cleaned_data.get("address_line2", "")
                    profile.city = form.cleaned_data.get("city", "")
                    profile.postcode = form.cleaned_data.get("postcode", "")
                    if form.cleaned_data.get("phone"):
                        profile.phone = form.cleaned_data["phone"]
                    profile.save()

            basket.clear()
            # Store reference in session so guests can access the confirmation
            request.session["last_order_reference"] = order.reference
            messages.success(request, f"Order #{order.reference} placed successfully!")
            return redirect("orders:confirmation", reference=order.reference)
    else:
        form = CheckoutForm(initial=initial)

    profile_has_address = False
    if request.user.is_authenticated:
        _p = getattr(request.user, "profile", None)
        profile_has_address = bool(_p and _p.address_line1)

    return render(request, "orders/checkout.html", {
        "form": form,
        "basket": basket,
        "delivery_charge": basket.get_delivery_charge("delivery"),
        "free_delivery_threshold": 20,
        "min_order_delivery": MIN_ORDER_DELIVERY,
        "is_open": is_open,
        "next_open_text": next_open_text,
        "profile_has_address": profile_has_address,
    })


def order_confirmation(request, reference):
    """Receipt page shown after a successful order.
    Accessible by the owning user, or by guest if reference matches session.
    """
    if request.user.is_authenticated:
        order = get_object_or_404(Order, reference=reference, user=request.user)
    else:
        # Guests can only see the order they just placed (reference in session)
        session_ref = request.session.get("last_order_reference")
        if session_ref != reference:
            messages.error(request, "Order not found.")
            return redirect("menu:menu")
        order = get_object_or_404(Order, reference=reference, user__isnull=True)
    est_minutes = _est_for_status(order)
    est_arrival = timezone.now() + timedelta(minutes=est_minutes)
    return render(request, "orders/confirmation.html", {
        "order": order,
        "est_arrival": est_arrival,
        "est_minutes": est_minutes,
        "status_steps": _build_status_steps(order),
    })


@login_required
def order_history(request):
    """Lists all past orders for the logged-in user."""
    orders = Order.objects.filter(user=request.user).prefetch_related("items")
    return render(request, "orders/history.html", {"orders": orders})


def _build_status_steps(order):
    """Return a list of step dicts for the status tracker widget."""
    if order.delivery_type == Order.COLLECTION:
        keys = ["pending", "confirmed", "preparing", "ready", "completed"]
        labels = ["Pending", "Confirmed", "Preparing", "Ready", "Done"]
    else:
        keys = ["pending", "confirmed", "preparing", "out_for_delivery", "completed"]
        labels = ["Pending", "Confirmed", "Preparing", "Out for Delivery", "Done"]

    try:
        current_idx = keys.index(order.status)
    except ValueError:
        current_idx = -1  # cancelled or unknown

    steps = []
    for i, (key, label) in enumerate(zip(keys, labels)):
        steps.append({
            "key": key,
            "label": label,
            "done": i < current_idx,
            "active": i == current_idx,
        })
    return steps


@login_required
def order_detail(request, reference):
    """Full detail view of a single past order."""
    order = get_object_or_404(Order, reference=reference, user=request.user)
    return render(request, "orders/order_detail.html", {
        "order": order,
        "status_steps": _build_status_steps(order),
    })


@login_required
@require_POST
def reorder(request, reference):
    """Re-adds all items from a previous order into the basket, then redirects to basket."""
    order = get_object_or_404(Order, reference=reference, user=request.user)
    basket = Basket(request)
    added = 0
    for item in order.items.all():
        if item.menu_item and item.menu_item.is_available:
            basket.add(item.menu_item, quantity=item.quantity)
            added += 1
    if added:
        messages.success(request, f"{added} item{'s' if added != 1 else ''} from order #{reference} added to your basket.")
    else:
        messages.warning(request, "None of the items from that order are currently available.")
    return redirect("orders:basket")


def order_status_api(request, reference):
    """JSON endpoint for the status-tracker polling — returns current status and est time."""
    if request.user.is_authenticated:
        order = get_object_or_404(Order, reference=reference, user=request.user)
    else:
        session_ref = request.session.get("last_order_reference")
        if session_ref != reference:
            return JsonResponse({"error": "not found"}, status=404)
        order = get_object_or_404(Order, reference=reference, user__isnull=True)
    est_minutes = _est_for_status(order)
    est_arrival = timezone.now() + timedelta(minutes=est_minutes)
    return JsonResponse({
        "status": order.status,
        "status_display": order.get_status_display(),
        "est_minutes": est_minutes,
        "est_arrival": est_arrival.strftime("%-I:%M %p"),
    })


def deal_picker(request, item_id):
    """
    Shows a form for the customer to choose items within a set-menu deal,
    then adds the deal to the basket with their choices stored as a note.
    """
    deal = get_object_or_404(MenuItem, pk=item_id, is_available=True)
    slots = list(deal.slots.prefetch_related("categories").order_by("order", "pk"))

    if not slots:
        # No slots configured — just add it directly and go to basket
        basket = Basket(request)
        basket.add(deal, quantity=1)
        messages.success(request, f"{deal.name} added to your basket.")
        return redirect("orders:basket")

    # Build choices list per slot (list of MenuItems)
    slot_choices = []
    for slot in slots:
        choices = list(slot.get_choices())
        slot_choices.append((slot, choices))

    if request.method == "POST":
        notes_parts = []
        errors = []
        for slot, choices in slot_choices:
            chosen_pk = request.POST.get(f"slot_{slot.pk}")
            if not chosen_pk:
                errors.append(f"Please select an item for '{slot.label}'.")
                continue
            choice_map = {str(c.pk): c for c in choices}
            chosen = choice_map.get(chosen_pk)
            if not chosen:
                errors.append(f"Invalid selection for '{slot.label}'.")
            else:
                notes_parts.append(f"{slot.label}: {chosen.name}")

        if errors:
            for e in errors:
                messages.error(request, e)
        else:
            basket = Basket(request)
            basket.add(deal, quantity=1)
            note = "Choices — " + ", ".join(notes_parts)
            basket.set_notes(item_id, note)
            messages.success(request, f"{deal.name} added to your basket.")
            return redirect("orders:basket")

    return render(request, "orders/deal_picker.html", {
        "deal": deal,
        "slot_choices": slot_choices,
    })


# ---------------------------------------------------------------------------
# Kitchen Display Screen
# ---------------------------------------------------------------------------

KITCHEN_STATUSES = ["pending", "confirmed", "preparing", "ready"]
KITCHEN_NEXT_STATUS = {
    "pending": "confirmed",
    "confirmed": "preparing",
    "preparing": "ready",
    "ready": "completed",
}


@staff_member_required
def kitchen_display(request):
    """Full-page kitchen view — designed to be left open on a tablet.
    Shows all active (non-complete, non-cancelled) orders as large cards.
    Auto-refreshes every 5 s via JS.
    """
    active_orders = (
        Order.objects
        .filter(status__in=KITCHEN_STATUSES)
        .prefetch_related("items")
        .order_by("created_at")
    )
    return render(request, "orders/kitchen_display.html", {
        "active_orders": active_orders,
        "kitchen_next_status": KITCHEN_NEXT_STATUS,
    })


@staff_member_required
@require_POST
def kitchen_update_status(request, reference):
    """AJAX endpoint — advance an order to the next kitchen status."""
    order = get_object_or_404(Order, reference=reference)
    next_status = KITCHEN_NEXT_STATUS.get(order.status)
    if next_status:
        order.status = next_status
        order.save(update_fields=["status"])
        return JsonResponse({"ok": True, "new_status": order.status})
    return JsonResponse({"ok": False, "error": "No next status"}, status=400)


@staff_member_required
@require_POST
def kitchen_cancel_order(request, reference):
    """AJAX endpoint — cancel an order from the kitchen display."""
    order = get_object_or_404(Order, reference=reference)
    if order.status not in (Order.STATUS_COMPLETED, Order.STATUS_CANCELLED):
        order.status = Order.STATUS_CANCELLED
        order.save(update_fields=["status"])
        return JsonResponse({"ok": True})
    return JsonResponse({"ok": False, "error": "Order cannot be cancelled"}, status=400)


@staff_member_required
def kitchen_orders_partial(request):
    """Returns only the order-cards HTML fragment for AJAX polling.
    Called every 5 s by the kitchen display JS to update the grid
    without a full page reload.
    """
    active_orders = (
        Order.objects
        .filter(status__in=KITCHEN_STATUSES)
        .prefetch_related("items")
        .order_by("created_at")
    )
    return render(request, "orders/kitchen_partial.html", {
        "active_orders": active_orders,
    })
