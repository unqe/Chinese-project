"""
Unit tests for the reviews app.
Covers the Review model properties, one-review-per-order constraint,
and the public reviews list view.
"""

from decimal import Decimal
from django.test import TestCase
from django.contrib.auth.models import User
from django.db import IntegrityError

from orders.models import Order
from reviews.models import Review


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def make_user(username="reviewer"):
    return User.objects.create_user(username=username, password="pass123")


def make_order(user):
    return Order.objects.create(
        user=user,
        full_name="Test Customer",
        phone="07700000000",
        email="test@example.com",
        subtotal=Decimal("15.00"),
        total=Decimal("17.50"),
        status=Order.STATUS_COMPLETED,
    )


def make_review(user, order, rating=4, approved=True):
    return Review.objects.create(
        user=user,
        order=order,
        rating=rating,
        title="Great food!",
        body="Really enjoyed the meal.",
        is_approved=approved,
    )


# ---------------------------------------------------------------------------
# Review model
# ---------------------------------------------------------------------------

class ReviewModelTest(TestCase):
    def setUp(self):
        self.user = make_user()
        self.order = make_order(self.user)

    def test_str_includes_username_and_rating(self):
        review = make_review(self.user, self.order, rating=5)
        self.assertIn(self.user.username, str(review))
        self.assertIn("5", str(review))

    def test_str_includes_order_reference(self):
        review = make_review(self.user, self.order)
        self.assertIn(self.order.reference, str(review))

    def test_default_not_approved(self):
        review = Review.objects.create(
            user=self.user,
            order=self.order,
            rating=3,
            title="OK",
            body="Not bad.",
        )
        self.assertFalse(review.is_approved)

    def test_owner_reply_blank_by_default(self):
        review = make_review(self.user, self.order)
        self.assertEqual(review.owner_reply, "")


# ---------------------------------------------------------------------------
# Review.star_range and empty_star_range properties
# ---------------------------------------------------------------------------

class ReviewStarRangeTest(TestCase):
    def setUp(self):
        self.user = make_user("staruser")
        self.order = make_order(self.user)

    def _review(self, rating):
        return Review(
            user=self.user, order=self.order,
            rating=rating, title="T", body="B",
        )

    def test_star_range_length_equals_rating(self):
        for r in range(1, 6):
            self.assertEqual(len(list(self._review(r).star_range)), r)

    def test_empty_star_range_length(self):
        for r in range(1, 6):
            self.assertEqual(len(list(self._review(r).empty_star_range)), 5 - r)

    def test_star_plus_empty_always_five(self):
        for r in range(1, 6):
            rev = self._review(r)
            total = len(list(rev.star_range)) + len(list(rev.empty_star_range))
            self.assertEqual(total, 5)


# ---------------------------------------------------------------------------
# One review per order constraint
# ---------------------------------------------------------------------------

class OneReviewPerOrderTest(TestCase):
    def setUp(self):
        self.user = make_user("dupuser")
        self.order = make_order(self.user)

    def test_second_review_same_order_raises(self):
        make_review(self.user, self.order, rating=5)
        with self.assertRaises(IntegrityError):
            Review.objects.create(
                user=self.user,
                order=self.order,
                rating=3,
                title="Another",
                body="Duplicate.",
            )


# ---------------------------------------------------------------------------
# Reviews list view
# ---------------------------------------------------------------------------

class ReviewsListViewTest(TestCase):
    def setUp(self):
        self.user = make_user("listuser")
        self.order1 = make_order(self.user)
        self.user2 = make_user("listuser2")
        self.order2 = make_order(self.user2)

    def test_reviews_page_loads(self):
        response = self.client.get("/reviews/")
        self.assertEqual(response.status_code, 200)

    def test_approved_review_shown(self):
        make_review(self.user, self.order1, rating=5, approved=True)
        response = self.client.get("/reviews/")
        self.assertContains(response, "Great food!")

    def test_unapproved_review_not_shown(self):
        make_review(self.user, self.order1, rating=2, approved=False)
        response = self.client.get("/reviews/")
        self.assertNotContains(response, "Great food!")

    def test_multiple_approved_reviews_shown(self):
        make_review(self.user, self.order1, rating=4, approved=True)
        Review.objects.create(
            user=self.user2, order=self.order2,
            rating=5, title="Excellent!", body="Will order again.", is_approved=True,
        )
        response = self.client.get("/reviews/")
        self.assertContains(response, "Great food!")
        self.assertContains(response, "Excellent!")
