"""
Orders app views — basket, checkout, confirmation, and order history.
"""

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse
from django.views.decorators.http import require_POST

from .basket import Basket
from .models import Order, OrderItem
from .forms import CheckoutForm
from menu.models import MenuItem


def basket_view(request):
    """Displays the current basket contents."""
    basket = Basket(request)
    return render(request, "orders/basket.html", {"basket": basket})


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
        return JsonResponse({
            "success": True,
            "basket_count": basket.get_total_quantity(),
            "message": f"{item.name} added to basket."
        })

    messages.success(request, f"\u2713 {item.name} added to your basket.")
    return redirect("menu:menu")


@require_POST
def basket_update(request, item_id):
    """Updates the quantity of a basket item."""
    basket = Basket(request)
    quantity = int(request.POST.get("quantity", 1))
    basket.update(item_id, quantity)
    return redirect("orders:basket")


@require_POST
def basket_remove(request, item_id):
    """Removes an item from the basket entirely."""
    basket = Basket(request)
    basket.remove(item_id)
    messages.info(request, "Item removed from basket.")
    return redirect("orders:basket")


@login_required
def checkout(request):
    """
    Checkout page. Pre-fills with saved profile data.
    Creates the Order and OrderItems on POST, then clears the basket.
    """
    basket = Basket(request)

    if not basket:
        messages.warning(request, "Your basket is empty.")
        return redirect("menu:menu")

    profile = getattr(request.user, "profile", None)
    initial = {}
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
            order.user = request.user
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
                )

            basket.clear()
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


@login_required
def order_confirmation(request, reference):
    """Receipt page shown after a successful order."""
    order = get_object_or_404(Order, reference=reference, user=request.user)
    return render(request, "orders/confirmation.html", {"order": order})


@login_required
def order_history(request):
    """Lists all past orders for the logged-in user."""
    orders = Order.objects.filter(user=request.user).prefetch_related("items")
    return render(request, "orders/history.html", {"orders": orders})


@login_required
def order_detail(request, reference):
    """Full detail view of a single past order."""
    order = get_object_or_404(Order, reference=reference, user=request.user)
    return render(request, "orders/order_detail.html", {"order": order})

