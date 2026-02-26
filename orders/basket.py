"""
Session-based shopping basket.
The basket is stored in the Django session as a dictionary keyed by
menu item ID. No database writes occur until the user places the order.
"""

from decimal import Decimal
from menu.models import MenuItem

BASKET_SESSION_KEY = "despair_basket"
PROMO_SESSION_KEY  = "despair_promo"
DELIVERY_CHARGE = Decimal("2.50")
FREE_DELIVERY_THRESHOLD = Decimal("20.00")
MIN_ORDER_DELIVERY = Decimal("10.00")


class Basket:
    """
    Manages the customer's basket using Django's session framework.
    Items are stored as { item_id: { 'quantity': int, 'price': str } }.
    """

    def __init__(self, request):
        self.session = request.session
        basket = self.session.get(BASKET_SESSION_KEY)
        if basket is None:
            basket = self.session[BASKET_SESSION_KEY] = {}
        # Sanitize: prices must always be strings — a previous bug could leave
        # Decimal objects in the session, causing JSON serialization errors.
        for item_data in basket.values():
            if not isinstance(item_data.get("price", ""), str):
                item_data["price"] = str(item_data["price"])
                self.session.modified = True
        self.basket = basket

    # ------------------------------------------------------------------
    # Mutation methods
    # ------------------------------------------------------------------

    def add(self, item, quantity=1):
        """Add a menu item to the basket or update its quantity."""
        item_id = str(item.pk)
        if item_id not in self.basket:
            self.basket[item_id] = {"quantity": 0, "price": str(item.price)}
        self.basket[item_id]["quantity"] += quantity
        self._save()

    def update(self, item_id, quantity):
        """Set the quantity of a basket item directly."""
        item_id = str(item_id)
        if item_id in self.basket:
            if quantity > 0:
                self.basket[item_id]["quantity"] = quantity
            else:
                self.remove(item_id)
        self._save()

    def set_notes(self, item_id, notes):
        """Attach a per-item note (e.g. 'no onions') to a basket entry."""
        item_id = str(item_id)
        if item_id in self.basket:
            self.basket[item_id]["notes"] = notes.strip()
            self._save()

    def remove(self, item_id):
        """Remove an item from the basket entirely."""
        item_id = str(item_id)
        if item_id in self.basket:
            del self.basket[item_id]
            self._save()

    def clear(self):
        """Empty the basket after a successful order."""
        del self.session[BASKET_SESSION_KEY]
        if PROMO_SESSION_KEY in self.session:
            del self.session[PROMO_SESSION_KEY]
        self.session.modified = True

    # ------------------------------------------------------------------
    # Promo code helpers
    # ------------------------------------------------------------------

    def apply_promo(self, code_str, discount_amount):
        """Store a validated promo code + calculated discount in the session."""
        self.session[PROMO_SESSION_KEY] = {
            "code": code_str.upper(),
            "discount": str(discount_amount),
        }
        self.session.modified = True

    def remove_promo(self):
        """Clear any applied promo code from the session."""
        if PROMO_SESSION_KEY in self.session:
            del self.session[PROMO_SESSION_KEY]
        self.session.modified = True

    @property
    def promo_code(self):
        """The applied promo code string, or empty string."""
        data = self.session.get(PROMO_SESSION_KEY)
        return data["code"] if data else ""

    def get_discount(self):
        """Return the promo discount amount as Decimal (0 if none applied)."""
        data = self.session.get(PROMO_SESSION_KEY)
        if data:
            return Decimal(data["discount"])
        return Decimal("0.00")

    def _save(self):
        """Mark the session as modified so Django persists the change."""
        self.session.modified = True

    # ------------------------------------------------------------------
    # Query methods
    # ------------------------------------------------------------------

    def __iter__(self):
        """
        Iterate over basket items, resolving each item_id to its
        MenuItem object and attaching the line total.
        Only yields items that still exist in the database.
        Never mutates the session basket dict.
        """
        item_ids = self.basket.keys()
        items = MenuItem.objects.filter(pk__in=item_ids)
        item_map = {str(item.pk): item for item in items}

        for item_id, raw in self.basket.items():
            menu_item = item_map.get(item_id)
            if menu_item is None:
                continue  # item was deleted from the menu
            # Work with a fresh copy — never mutate the session dict
            entry = dict(raw)
            entry["menu_item"] = menu_item
            entry["price"] = Decimal(raw["price"])
            entry["total_price"] = entry["price"] * entry["quantity"]
            entry["notes"] = raw.get("notes", "")
            yield entry

    def get_total_quantity(self):
        """Total number of individual items (sum of all quantities)."""
        return sum(item["quantity"] for item in self.basket.values())

    def get_subtotal(self):
        """Basket subtotal before delivery charge."""
        return sum(
            Decimal(data["price"]) * data["quantity"]
            for data in self.basket.values()
        )

    def get_delivery_charge(self, delivery_type="delivery"):
        """
        Returns the delivery charge.
        Delivery is free over FREE_DELIVERY_THRESHOLD.
        Collection is always free.
        """
        if delivery_type == "collection":
            return Decimal("0.00")
        subtotal = self.get_subtotal()
        if subtotal >= FREE_DELIVERY_THRESHOLD:
            return Decimal("0.00")
        return DELIVERY_CHARGE

    def get_total(self, delivery_type="delivery"):
        """Total including delivery charge and minus any promo discount."""
        before_discount = self.get_subtotal() + self.get_delivery_charge(delivery_type)
        return max(Decimal("0.00"), before_discount - self.get_discount())

    def __len__(self):
        return self.get_total_quantity()

    def __bool__(self):
        return bool(self.basket)
