"""
Unit tests for the orders app.
Covers the Basket class, PromoCode model validation, Order model,
OrderItem model, and core basket views.
"""

from decimal import Decimal
from unittest.mock import MagicMock
from django.test import TestCase
from django.contrib.auth.models import User
from django.utils import timezone

from menu.models import Category, MenuItem
from orders.models import Order, OrderItem, PromoCode
from orders.basket import (
    Basket,
    BASKET_SESSION_KEY,
    PROMO_SESSION_KEY,
    DELIVERY_CHARGE,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

class MockSession(dict):
    """A plain dict that also supports session.modified = True."""
    modified = False


def make_mock_request(session_data=None):
    """Return a mock request object with a session that supports .modified."""
    request = MagicMock()
    if session_data is not None:
        # Wrap the supplied dict in MockSession so .modified works
        sess = MockSession(session_data)
        request.session = sess
    else:
        request.session = MockSession()
    return request


def make_category(name="Mains"):
    return Category.objects.create(name=name, order=1)


def make_item(category, name="Kung Pao Chicken", price="9.90"):
    return MenuItem.objects.create(
        category=category,
        name=name,
        price=Decimal(price),
        is_available=True,
    )


# ---------------------------------------------------------------------------
# Basket — add
# ---------------------------------------------------------------------------

class BasketAddTest(TestCase):
    def setUp(self):
        cat = make_category()
        self.item = make_item(cat)

    def test_add_item_creates_entry(self):
        basket = Basket(make_mock_request())
        basket.add(self.item, quantity=1)
        self.assertIn(str(self.item.pk), basket.basket)

    def test_add_item_stores_correct_quantity(self):
        basket = Basket(make_mock_request())
        basket.add(self.item, quantity=3)
        self.assertEqual(basket.basket[str(self.item.pk)]["quantity"], 3)

    def test_add_item_twice_accumulates_quantity(self):
        basket = Basket(make_mock_request())
        basket.add(self.item, quantity=2)
        basket.add(self.item, quantity=1)
        self.assertEqual(basket.basket[str(self.item.pk)]["quantity"], 3)

    def test_add_stores_price_as_string(self):
        basket = Basket(make_mock_request())
        basket.add(self.item)
        price = basket.basket[str(self.item.pk)]["price"]
        self.assertIsInstance(price, str)

    def test_len_reflects_total_quantity(self):
        basket = Basket(make_mock_request())
        basket.add(self.item, quantity=4)
        self.assertEqual(len(basket), 4)

    def test_bool_true_when_not_empty(self):
        basket = Basket(make_mock_request())
        basket.add(self.item)
        self.assertTrue(bool(basket))

    def test_bool_false_when_empty(self):
        basket = Basket(make_mock_request())
        self.assertFalse(bool(basket))


# ---------------------------------------------------------------------------
# Basket — update
# ---------------------------------------------------------------------------

class BasketUpdateTest(TestCase):
    def setUp(self):
        cat = make_category()
        self.item = make_item(cat)

    def test_update_changes_quantity(self):
        basket = Basket(make_mock_request())
        basket.add(self.item, quantity=2)
        basket.update(self.item.pk, 5)
        self.assertEqual(basket.basket[str(self.item.pk)]["quantity"], 5)

    def test_update_to_zero_removes_item(self):
        basket = Basket(make_mock_request())
        basket.add(self.item, quantity=2)
        basket.update(self.item.pk, 0)
        self.assertNotIn(str(self.item.pk), basket.basket)

    def test_update_nonexistent_key_is_safe(self):
        basket = Basket(make_mock_request())
        basket.update(99999, 2)  # should not raise


# ---------------------------------------------------------------------------
# Basket — remove
# ---------------------------------------------------------------------------

class BasketRemoveTest(TestCase):
    def setUp(self):
        cat = make_category()
        self.item = make_item(cat)

    def test_remove_deletes_entry(self):
        basket = Basket(make_mock_request())
        basket.add(self.item)
        basket.remove(self.item.pk)
        self.assertNotIn(str(self.item.pk), basket.basket)

    def test_remove_nonexistent_is_safe(self):
        basket = Basket(make_mock_request())
        basket.remove(99999)  # should not raise


# ---------------------------------------------------------------------------
# Basket — totals
# ---------------------------------------------------------------------------

class BasketTotalsTest(TestCase):
    def setUp(self):
        cat = make_category()
        self.cheap = make_item(cat, name="Spring Roll", price="4.00")
        self.mid = make_item(cat, name="Sweet & Sour Pork", price="9.50")

    def test_subtotal_single_item(self):
        basket = Basket(make_mock_request())
        basket.add(self.cheap, quantity=2)
        self.assertEqual(basket.get_subtotal(), Decimal("8.00"))

    def test_subtotal_multiple_items(self):
        basket = Basket(make_mock_request())
        basket.add(self.cheap, quantity=1)
        basket.add(self.mid, quantity=1)
        self.assertEqual(basket.get_subtotal(), Decimal("13.50"))

    def test_delivery_charge_below_threshold(self):
        basket = Basket(make_mock_request())
        basket.add(self.cheap, quantity=1)  # £4 < £20
        self.assertEqual(basket.get_delivery_charge("delivery"), DELIVERY_CHARGE)

    def test_free_delivery_above_threshold(self):
        basket = Basket(make_mock_request())
        basket.add(self.mid, quantity=3)  # £28.50 > £20
        self.assertEqual(basket.get_delivery_charge("delivery"), Decimal("0.00"))

    def test_collection_always_free(self):
        basket = Basket(make_mock_request())
        basket.add(self.cheap, quantity=1)
        self.assertEqual(basket.get_delivery_charge("collection"), Decimal("0.00"))

    def test_total_includes_delivery(self):
        basket = Basket(make_mock_request())
        basket.add(self.cheap, quantity=1)  # £4
        self.assertEqual(basket.get_total("delivery"), Decimal("4.00") + DELIVERY_CHARGE)

    def test_total_deducts_discount(self):
        basket = Basket(make_mock_request())
        basket.add(self.mid, quantity=1)  # £9.50 collection
        basket.apply_promo("TEST10", Decimal("2.00"))
        self.assertEqual(basket.get_total("collection"), Decimal("7.50"))

    def test_total_never_negative(self):
        basket = Basket(make_mock_request())
        basket.add(self.cheap, quantity=1)  # £4
        basket.apply_promo("BIGSAVE", Decimal("100.00"))
        self.assertGreaterEqual(basket.get_total("collection"), Decimal("0.00"))


# ---------------------------------------------------------------------------
# Basket — promo
# ---------------------------------------------------------------------------

class BasketPromoTest(TestCase):
    def test_apply_stores_code_and_amount(self):
        basket = Basket(make_mock_request())
        basket.apply_promo("SAVE5", Decimal("5.00"))
        self.assertEqual(basket.promo_code, "SAVE5")
        self.assertEqual(basket.get_discount(), Decimal("5.00"))

    def test_apply_uppercases_code(self):
        basket = Basket(make_mock_request())
        basket.apply_promo("save5", Decimal("3.00"))
        self.assertEqual(basket.promo_code, "SAVE5")

    def test_remove_clears_promo(self):
        basket = Basket(make_mock_request())
        basket.apply_promo("SAVE5", Decimal("5.00"))
        basket.remove_promo()
        self.assertEqual(basket.promo_code, "")
        self.assertEqual(basket.get_discount(), Decimal("0.00"))

    def test_no_promo_zero_discount(self):
        basket = Basket(make_mock_request())
        self.assertEqual(basket.get_discount(), Decimal("0.00"))


# ---------------------------------------------------------------------------
# Basket — clear
# ---------------------------------------------------------------------------

class BasketClearTest(TestCase):
    def setUp(self):
        cat = make_category()
        self.item = make_item(cat)

    def test_clear_empties_basket_session_key(self):
        req = make_mock_request()
        basket = Basket(req)
        basket.add(self.item)
        basket.clear()
        self.assertNotIn(BASKET_SESSION_KEY, req.session)

    def test_clear_removes_promo_session_key(self):
        req = make_mock_request()
        basket = Basket(req)
        basket.add(self.item)
        basket.apply_promo("SAVE5", Decimal("5.00"))
        basket.clear()
        self.assertNotIn(PROMO_SESSION_KEY, req.session)


# ---------------------------------------------------------------------------
# PromoCode — is_valid
# ---------------------------------------------------------------------------

class PromoCodeIsValidTest(TestCase):
    def _promo(self, **kw):
        defaults = dict(
            code="TEST",
            discount_type=PromoCode.PERCENT,
            value=Decimal("10"),
            active=True,
            min_order=Decimal("0"),
            max_uses=0,
            uses_count=0,
        )
        defaults.update(kw)
        return PromoCode(**defaults)

    def test_valid_active_promo(self):
        valid, _ = self._promo().is_valid(subtotal=Decimal("15.00"))
        self.assertTrue(valid)

    def test_inactive_rejected(self):
        valid, msg = self._promo(active=False).is_valid()
        self.assertFalse(valid)
        self.assertIn("no longer active", msg)

    def test_expired_rejected(self):
        past = timezone.now() - timezone.timedelta(days=1)
        valid, msg = self._promo(valid_until=past).is_valid()
        self.assertFalse(valid)
        self.assertIn("expired", msg)

    def test_future_start_rejected(self):
        future = timezone.now() + timezone.timedelta(days=1)
        valid, msg = self._promo(valid_from=future).is_valid()
        self.assertFalse(valid)
        self.assertIn("not yet valid", msg)

    def test_max_uses_exhausted_rejected(self):
        valid, msg = self._promo(max_uses=5, uses_count=5).is_valid()
        self.assertFalse(valid)
        self.assertIn("fully redeemed", msg)

    def test_min_order_not_met_rejected(self):
        valid, msg = self._promo(min_order=Decimal("20.00")).is_valid(subtotal=Decimal("10.00"))
        self.assertFalse(valid)
        self.assertIn("minimum order", msg)

    def test_min_order_exactly_met_accepted(self):
        valid, _ = self._promo(min_order=Decimal("10.00")).is_valid(subtotal=Decimal("10.00"))
        self.assertTrue(valid)


# ---------------------------------------------------------------------------
# PromoCode — get_discount
# ---------------------------------------------------------------------------

class PromoCodeGetDiscountTest(TestCase):
    def test_percent_discount(self):
        promo = PromoCode(
            code="TEN", discount_type=PromoCode.PERCENT, value=Decimal("10")
        )
        self.assertEqual(promo.get_discount(Decimal("50.00")), Decimal("5.00"))

    def test_fixed_discount(self):
        promo = PromoCode(
            code="THREE", discount_type=PromoCode.FIXED, value=Decimal("3.00")
        )
        self.assertEqual(promo.get_discount(Decimal("20.00")), Decimal("3.00"))

    def test_fixed_discount_capped_at_subtotal(self):
        promo = PromoCode(
            code="MEGA", discount_type=PromoCode.FIXED, value=Decimal("100.00")
        )
        self.assertEqual(promo.get_discount(Decimal("5.00")), Decimal("5.00"))


# ---------------------------------------------------------------------------
# Order model
# ---------------------------------------------------------------------------

class OrderModelTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="testuser", password="pass123")

    def _make_order(self, **kw):
        defaults = dict(
            user=self.user,
            full_name="Test User",
            phone="07700000000",
            email="test@example.com",
            subtotal=Decimal("10.00"),
            total=Decimal("12.50"),
        )
        defaults.update(kw)
        return Order.objects.create(**defaults)

    def test_reference_generated_on_save(self):
        order = self._make_order()
        self.assertTrue(order.reference)

    def test_reference_is_8_chars(self):
        order = self._make_order()
        self.assertEqual(len(order.reference), 8)

    def test_reference_is_uppercase(self):
        order = self._make_order()
        self.assertEqual(order.reference, order.reference.upper())

    def test_references_are_unique(self):
        o1 = self._make_order()
        o2 = self._make_order()
        self.assertNotEqual(o1.reference, o2.reference)

    def test_default_status_pending(self):
        order = self._make_order()
        self.assertEqual(order.status, Order.STATUS_PENDING)

    def test_is_delivery_true(self):
        self.assertTrue(Order(delivery_type=Order.DELIVERY).is_delivery)

    def test_is_delivery_false_for_collection(self):
        self.assertFalse(Order(delivery_type=Order.COLLECTION).is_delivery)


# ---------------------------------------------------------------------------
# OrderItem model
# ---------------------------------------------------------------------------

class OrderItemLineTotal(TestCase):
    def setUp(self):
        user = User.objects.create_user(username="u2", password="pass")
        self.order = Order.objects.create(
            user=user, full_name="D", phone="0", email="d@d.com",
            subtotal=Decimal("10"), total=Decimal("10"),
        )

    def test_line_total_correct(self):
        item = OrderItem(order=self.order, item_name="Fried Rice",
                         item_price=Decimal("6.50"), quantity=2)
        self.assertEqual(item.line_total, Decimal("13.00"))

    def test_line_total_quantity_one(self):
        item = OrderItem(order=self.order, item_name="Roast Duck",
                         item_price=Decimal("12.50"), quantity=1)
        self.assertEqual(item.line_total, Decimal("12.50"))


# ---------------------------------------------------------------------------
# Basket views (integration)
# ---------------------------------------------------------------------------

class BasketViewTest(TestCase):
    def setUp(self):
        cat = make_category("Starters")
        self.item = make_item(cat, name="Prawn Toast", price="5.00")

    def test_basket_page_loads(self):
        response = self.client.get("/orders/basket/")
        self.assertEqual(response.status_code, 200)

    def test_basket_add_returns_json(self):
        response = self.client.post(
            f"/orders/basket/add/{self.item.pk}/",
            {"quantity": 1},
            HTTP_X_REQUESTED_WITH="XMLHttpRequest",
        )
        self.assertEqual(response.status_code, 200)
        self.assertIn("item_quantity", response.json())

    def test_added_item_appears_in_basket(self):
        self.client.post(
            f"/orders/basket/add/{self.item.pk}/",
            {"quantity": 2},
            HTTP_X_REQUESTED_WITH="XMLHttpRequest",
        )
        response = self.client.get("/orders/basket/")
        self.assertContains(response, "Prawn Toast")

    def test_removed_item_gone_from_basket(self):
        self.client.post(
            f"/orders/basket/add/{self.item.pk}/",
            {"quantity": 1},
            HTTP_X_REQUESTED_WITH="XMLHttpRequest",
        )
        self.client.post(f"/orders/basket/remove/{self.item.pk}/")
        response = self.client.get("/orders/basket/")
        self.assertNotContains(response, "Prawn Toast")


class CheckoutViewTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="buyer", password="pass123")
        cat = make_category("Mains")
        self.item = make_item(cat, name="Chow Mein", price="8.00")

    def _add_item(self):
        self.client.post(
            f"/orders/basket/add/{self.item.pk}/",
            {"quantity": 1},
            HTTP_X_REQUESTED_WITH="XMLHttpRequest",
        )

    def test_checkout_empty_basket_redirects(self):
        self.client.login(username="buyer", password="pass123")
        response = self.client.get("/orders/checkout/")
        # Empty basket redirects to the menu page
        self.assertEqual(response.status_code, 302)

    def test_checkout_with_item_renders_form(self):
        self.client.login(username="buyer", password="pass123")
        self._add_item()
        response = self.client.get("/orders/checkout/")
        self.assertEqual(response.status_code, 200)
