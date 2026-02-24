"""
Reviews app model.
Reviews are tied to a specific Order so that only users who have
actually placed an order can leave a review — preventing spam.
One review per order is enforced at the database level.
"""

from django.db import models
from django.contrib.auth.models import User
from django.core.validators import MinValueValidator, MaxValueValidator
from orders.models import Order


class Review(models.Model):
    """
    A customer review linked to both the User and the Order they placed.
    Rating is 1-5 stars. Reviews are held pending admin approval by default,
    which prevents spam appearing on the public review page.
    """

    user = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name="reviews",
        null=True, blank=True
    )
    order = models.OneToOneField(
        Order, on_delete=models.CASCADE, related_name="review",
        help_text="Each order can only have one review."
    )
    rating = models.IntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(5)],
        help_text="1 to 5 stars."
    )
    title = models.CharField(max_length=150)
    body = models.TextField()
    is_approved = models.BooleanField(
        default=False,
        help_text="Tick to make this review visible on the public reviews page."
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        username = self.user.username if self.user else "Guest"
        return f"{username} — {self.rating}★ ({self.order.reference})"

    @property
    def star_range(self):
        """Returns a range used by templates to render filled star icons."""
        return range(self.rating)

    @property
    def empty_star_range(self):
        """Returns a range used by templates to render empty star icons."""
        return range(5 - self.rating)

