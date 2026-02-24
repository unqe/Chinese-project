"""
Orders app models — OpeningHours, Order, and OrderItem.
Orders are linked to the user account so they appear in order history.
OrderItem stores a snapshot of the item price at time of purchase,
so the receipt remains accurate even if prices change later.
"""

import uuid
from django.db import models
from django.contrib.auth.models import User
from menu.models import MenuItem


class OpeningHours(models.Model):
    """
    Stores opening hours for each day of the week.
    Editable in the admin panel without any code changes.
    A 'closed' flag lets admins mark days off easily.
    """

    DAYS = [
        (0, "Monday"),
        (1, "Tuesday"),
        (2, "Wednesday"),
        (3, "Thursday"),
        (4, "Friday"),
        (5, "Saturday"),
        (6, "Sunday"),
    ]

    day = models.IntegerField(choices=DAYS, unique=True)
    opening_time = models.TimeField(null=True, blank=True)
    closing_time = models.TimeField(null=True, blank=True)
    is_closed = models.BooleanField(default=False)

    class Meta:
        ordering = ["day"]
        verbose_name_plural = "Opening Hours"

    def __str__(self):
        if self.is_closed:
            return f"{self.get_day_display()}: Closed"
        return f"{self.get_day_display()}: {self.opening_time} \u2013 {self.closing_time}"


class Order(models.Model):
    """
    Represents a customer order. Linked to a User account.
    A unique reference number (UUID-based) is generated on creation
    and shown on the receipt page.

    Payment method covers three options:
    - card: simulated card payment (fake form at checkout)
    - cash_delivery: pay in cash when the driver arrives
    - cash_collection: pay in cash when collecting in store

    Delivery type determines whether an address is required.
    """

    PAYMENT_CARD = "card"
    PAYMENT_CASH_DELIVERY = "cash_delivery"
    PAYMENT_CASH_COLLECTION = "cash_collection"

    PAYMENT_CHOICES = [
        (PAYMENT_CARD, "Card Payment"),
        (PAYMENT_CASH_DELIVERY, "Cash on Delivery"),
        (PAYMENT_CASH_COLLECTION, "Cash on Collection"),
    ]

    DELIVERY = "delivery"
    COLLECTION = "collection"

    DELIVERY_CHOICES = [
        (DELIVERY, "Delivery"),
        (COLLECTION, "Collection"),
    ]

    STATUS_PENDING = "pending"
    STATUS_CONFIRMED = "confirmed"
    STATUS_PREPARING = "preparing"
    STATUS_OUT_FOR_DELIVERY = "out_for_delivery"
    STATUS_READY = "ready"
    STATUS_COMPLETED = "completed"
    STATUS_CANCELLED = "cancelled"

    STATUS_CHOICES = [
        (STATUS_PENDING, "Pending"),
        (STATUS_CONFIRMED, "Confirmed"),
        (STATUS_PREPARING, "Preparing"),
        (STATUS_OUT_FOR_DELIVERY, "Out for Delivery"),
        (STATUS_READY, "Ready for Collection"),
        (STATUS_COMPLETED, "Completed"),
        (STATUS_CANCELLED, "Cancelled"),
    ]

    reference = models.CharField(max_length=12, unique=True, editable=False)
    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name="orders")
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default=STATUS_PENDING)
    delivery_type = models.CharField(max_length=15, choices=DELIVERY_CHOICES, default=DELIVERY)
    payment_method = models.CharField(max_length=20, choices=PAYMENT_CHOICES, default=PAYMENT_CARD)

    # Delivery address fields — only required when delivery_type == DELIVERY
    address_line1 = models.CharField(max_length=200, blank=True)
    address_line2 = models.CharField(max_length=200, blank=True)
    city = models.CharField(max_length=100, blank=True)
    postcode = models.CharField(max_length=10, blank=True)

    # Contact details taken at checkout
    full_name = models.CharField(max_length=150)
    phone = models.CharField(max_length=20)
    email = models.EmailField()

    # Fake card details — stored only for the simulated receipt (not real)
    card_last_four = models.CharField(max_length=4, blank=True)

    special_instructions = models.TextField(blank=True)
    subtotal = models.DecimalField(max_digits=8, decimal_places=2, default=0)
    delivery_charge = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    total = models.DecimalField(max_digits=8, decimal_places=2, default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"Order #{self.reference} by {self.user}"

    def save(self, *args, **kwargs):
        """Generate a short unique reference on first save."""
        if not self.reference:
            self.reference = uuid.uuid4().hex[:8].upper()
        super().save(*args, **kwargs)

    @property
    def is_delivery(self):
        """Returns True if this is a delivery order."""
        return self.delivery_type == self.DELIVERY


class OrderItem(models.Model):
    """
    A line item within an Order.
    Price is snapshotted at order time so the receipt is always accurate,
    even if the menu price changes later.
    """

    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name="items")
    menu_item = models.ForeignKey(
        MenuItem, on_delete=models.SET_NULL, null=True, related_name="order_items"
    )
    item_name = models.CharField(max_length=200)      # snapshot of name at order time
    item_price = models.DecimalField(max_digits=6, decimal_places=2)  # snapshot
    quantity = models.PositiveIntegerField(default=1)
    notes = models.CharField(max_length=300, blank=True, help_text="Per-item special request (e.g. no onions)")

    class Meta:
        ordering = ["id"]

    def __str__(self):
        return f"{self.quantity}x {self.item_name}"

    @property
    def line_total(self):
        """Total cost for this line: price * quantity."""
        return self.item_price * self.quantity

