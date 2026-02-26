"""
Orders app models — OpeningHours, Order, and OrderItem.
Orders are linked to the user account so they appear in order history.
OrderItem stores a snapshot of the item price at time of purchase,
so the receipt remains accurate even if prices change later.
"""

import uuid
from decimal import Decimal
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
    discount_amount = models.DecimalField(max_digits=6, decimal_places=2, default=0)
    promo_code = models.CharField(max_length=30, blank=True)
    total = models.DecimalField(max_digits=8, decimal_places=2, default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"Order #{self.reference} — {self.full_name}"

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
        if self.item_price is None:
            return None
        return self.item_price * self.quantity


class PromoCode(models.Model):
    """
    Discount/promo codes redeemable at checkout.
    Supports percentage off or fixed-amount off discounts.
    """

    PERCENT = "percent"
    FIXED = "fixed"
    DISCOUNT_TYPE_CHOICES = [
        (PERCENT, "Percentage off"),
        (FIXED, "Fixed amount off (£)"),
    ]

    code = models.CharField(max_length=30, unique=True)
    description = models.CharField(max_length=200, blank=True)
    discount_type = models.CharField(max_length=10, choices=DISCOUNT_TYPE_CHOICES, default=PERCENT)
    value = models.DecimalField(
        max_digits=6,
        decimal_places=2,
        help_text="Percentage (e.g. 10 for 10% off) or fixed £ amount.",
    )
    min_order = models.DecimalField(
        max_digits=6, decimal_places=2, default=0,
        help_text="Minimum subtotal required.",
    )
    max_uses = models.PositiveIntegerField(default=0, help_text="0 = unlimited")
    uses_count = models.PositiveIntegerField(default=0)
    active = models.BooleanField(default=True)
    valid_from = models.DateTimeField(null=True, blank=True)
    valid_until = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        if self.discount_type == self.PERCENT:
            return f"{self.code} — {self.value}% off"
        return f"{self.code} — \u00a3{self.value} off"

    def is_valid(self, subtotal=None):
        """Check if the code can be used. Returns (bool, error_message)."""
        from django.utils import timezone
        now = timezone.now()
        if not self.active:
            return False, "This promo code is no longer active."
        if self.valid_from and now < self.valid_from:
            return False, "This promo code is not yet valid."
        if self.valid_until and now > self.valid_until:
            return False, "This promo code has expired."
        if self.max_uses > 0 and self.uses_count >= self.max_uses:
            return False, "This promo code has been fully redeemed."
        if subtotal is not None and subtotal < self.min_order:
            return False, f"This code requires a minimum order of \u00a3{self.min_order}."
        return True, ""

    def get_discount(self, subtotal):
        """Return the discount amount for the given subtotal."""
        from decimal import Decimal
        if self.discount_type == self.PERCENT:
            discount = subtotal * self.value / Decimal("100")
        else:
            discount = self.value
        return min(discount, subtotal).quantize(Decimal("0.01"))


class SiteAnnouncement(models.Model):
    """Admin-controlled banner displayed at the top of every public page."""

    STYLE_INFO = "info"
    STYLE_WARNING = "warning"
    STYLE_DANGER = "danger"
    STYLE_SUCCESS = "success"
    STYLE_CHOICES = [
        (STYLE_INFO, "Info (blue)"),
        (STYLE_WARNING, "Warning (yellow)"),
        (STYLE_DANGER, "Danger (red)"),
        (STYLE_SUCCESS, "Success (green)"),
    ]

    message = models.TextField(help_text="Supports plain text. Keep it short.")
    is_active = models.BooleanField(
        default=True,
        help_text="Only one announcement is shown at a time (the most recently created active one).",
    )
    style = models.CharField(
        max_length=10,
        choices=STYLE_CHOICES,
        default=STYLE_INFO,
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "Site Announcement"
        verbose_name_plural = "Site Announcements"

    def __str__(self):
        return self.message[:80]


class SpecialOffer(models.Model):
    """Auto-applied discount that activates at checkout when conditions are met.
    Unlike PromoCode, the customer never needs to enter a code — it applies automatically.
    """

    PERCENT = "percent"
    FIXED = "fixed"
    DISCOUNT_TYPE_CHOICES = [
        (PERCENT, "Percentage off (%)"),
        (FIXED, "Fixed amount off (£)"),
    ]

    name = models.CharField(max_length=100, help_text="Internal name, e.g. 'Weekend Deal'")
    badge_text = models.CharField(
        max_length=50,
        blank=True,
        help_text="Short label shown to customers at checkout, e.g. '🎉 Happy Hour'. Defaults to name if blank.",
    )
    description = models.TextField(blank=True, help_text="Optional public description shown at checkout.")
    discount_type = models.CharField(max_length=10, choices=DISCOUNT_TYPE_CHOICES, default=PERCENT)
    value = models.DecimalField(
        max_digits=6, decimal_places=2,
        help_text="Percentage (e.g. 10 = 10%) or fixed amount in pounds (e.g. 2.50)",
    )
    min_order = models.DecimalField(
        max_digits=6, decimal_places=2, default=Decimal("0.00"),
        help_text="Minimum basket subtotal (£) required. Set to 0 for no minimum.",
    )
    active = models.BooleanField(default=True)
    valid_from = models.DateTimeField(null=True, blank=True, help_text="Leave blank to activate immediately.")
    valid_until = models.DateTimeField(null=True, blank=True, help_text="Leave blank for no expiry.")
    uses_count = models.PositiveIntegerField(default=0, editable=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "Special Offer"
        verbose_name_plural = "Special Offers"

    def __str__(self):
        if self.discount_type == self.PERCENT:
            return f"{self.name} ({self.value}% off)"
        return f"{self.name} (£{self.value} off)"

    def get_badge(self):
        """Return the customer-facing badge text."""
        return self.badge_text or self.name

    def is_applicable(self, subtotal):
        """Return (True, '') if this offer can be applied to the given subtotal,
        otherwise (False, reason_string)."""
        from django.utils import timezone as tz
        now = tz.now()
        if not self.active:
            return False, "Offer is not active"
        if self.valid_from and now < self.valid_from:
            return False, "Offer has not started yet"
        if self.valid_until and now > self.valid_until:
            return False, "Offer has expired"
        if subtotal < self.min_order:
            return False, f"Minimum order £{self.min_order} required"
        return True, ""

    def calculate_discount(self, subtotal):
        """Return the discount amount (as Decimal) for the given subtotal."""
        if self.discount_type == self.PERCENT:
            return (subtotal * self.value / Decimal("100")).quantize(Decimal("0.01"))
        return min(self.value, subtotal)
