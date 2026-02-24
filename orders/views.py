"""
Orders app views — basket, checkout, confirmation, and order history.
"""

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse
from django.views.decorators.http import require_POST
import datetime

from .basket import Basket
from .models import Order, OrderItem
from .forms import CheckoutForm
from menu.models import MenuItem


def basket_view(request):
    """Displays the current basket contents."""
    basket = Basket(request)
    basket_item_ids = set(basket.basket.keys())
    popular_items = (
        MenuItem.objects
        .filter(is_popular=True, is_available=True)
        .exclude(pk__in=basket_item_ids)[:4]
    )
    return render(request, "orders/basket.html", {
        "basket": basket,
        "popular_items": popular_items,
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
        item_qty = basket.basket.get(str(item_id), {}).get("quantity", 0)
        return JsonResponse({
            "success": True,
            "basket_count": basket.get_total_quantity(),
            "basket_subtotal": str(basket.get_subtotal()),
            "item_quantity": item_qty,
            "message": f"{item.name} added to basket."
        })

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

    if request.headers.get("X-Requested-With") == "XMLHttpRequest":
        item_qty = basket.basket.get(str(item_id), {}).get("quantity", 0)
        return JsonResponse({
            "success": True,
            "basket_count": basket.get_total_quantity(),
            "basket_subtotal": str(basket.get_subtotal()),
            "item_quantity": item_qty,
        })
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

    if request.headers.get("X-Requested-With") == "XMLHttpRequest":
        return JsonResponse({
            "success": True,
            "basket_count": basket.get_total_quantity(),
            "basket_subtotal": str(basket.get_subtotal()),
            "item_quantity": 0,
        })
    messages.info(request, "Item removed from basket.")
    return redirect("orders:basket")


def checkout(request):
    """
    Checkout page. Pre-fills with saved profile data for logged-in users.
    Guests can also checkout — they just need to enter an email.
    Creates the Order and OrderItems on POST, then clears the basket.
    """
    basket = Basket(request)

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
        form = CheckoutForm(request.POST)
        if form.is_valid():
            order = form.save(commit=False)
            order.user = request.user if request.user.is_authenticated else None
            delivery_type = form.cleaned_data["delivery_type"]
            order.subtotal = basket.get_subtotal()
            order.delivery_charge = basket.get_delivery_charge(delivery_type)
            order.total = basket.get_total(delivery_type)

            if form.cleaned_data.get("payment_method") == Order.PAYMENT_CARD:
                raw_card = form.cleaned_data.get("card_number", "").replace(" ", "")
                order.card_last_four = raw_card[-4:] if raw_card else ""

            order.save()

            for item_data in basket:
                OrderItem.objects.create(
                    order=order,
                    menu_item=item_data["menu_item"],
                    item_name=item_data["menu_item"].name,
                    item_price=item_data["price"],
                    quantity=item_data["quantity"],
                    notes=item_data.get("notes", ""),
                )

            basket.clear()
            # Store reference in session so guests can access the confirmation
            request.session["last_order_reference"] = order.reference
            messages.success(request, f"Order #{order.reference} placed successfully!")
            return redirect("orders:confirmation", reference=order.reference)
    else:
        form = CheckoutForm(initial=initial)

    return render(request, "orders/checkout.html", {
        "form": form,
        "basket": basket,
        "delivery_charge": basket.get_delivery_charge("delivery"),
        "free_delivery_threshold": 20,
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
    est_minutes = 45 if order.is_delivery else 15
    est_arrival = order.created_at + datetime.timedelta(minutes=est_minutes)
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
    """JSON endpoint for the status-tracker polling — returns current status."""
    if request.user.is_authenticated:
        order = get_object_or_404(Order, reference=reference, user=request.user)
    else:
        session_ref = request.session.get("last_order_reference")
        if session_ref != reference:
            return JsonResponse({"error": "not found"}, status=404)
        order = get_object_or_404(Order, reference=reference, user__isnull=True)
    return JsonResponse({
        "status": order.status,
        "status_display": order.get_status_display(),
    })

