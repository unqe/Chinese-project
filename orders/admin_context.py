"""
Context processor that injects live stats into every admin template.
Stats are only computed when the request path starts with the admin prefix
to avoid unnecessary DB queries on front-end pages.
"""

from django.utils import timezone
from datetime import timedelta
from decimal import Decimal


def admin_stats(request):
    """
    Injects a ``stats`` dict into admin templates.
    Silently returns empty dict on any error so the admin never breaks.
    """
    # Only run for admin pages
    if not (request.path.startswith("/kitchen-panel/") or
            request.path.startswith("/en/kitchen-panel/") or
            request.path.startswith("/zh-hans/kitchen-panel/")):
        return {}

    try:
        from orders.models import Order, OrderItem
        from orders.models import PromoCode
        from reviews.models import Review
        from django.db.models import Sum, Count, Avg

        now        = timezone.now()
        today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
        week_start  = today_start - timedelta(days=now.weekday())   # Monday
        month_ago   = now - timedelta(days=30)

        # Today
        today_qs      = Order.objects.filter(created_at__gte=today_start)
        today_orders  = today_qs.count()
        today_revenue = today_qs.aggregate(s=Sum("total"))["s"] or Decimal("0.00")

        # This week
        week_qs      = Order.objects.filter(created_at__gte=week_start)
        week_orders  = week_qs.count()
        week_revenue = week_qs.aggregate(s=Sum("total"))["s"] or Decimal("0.00")

        # This month
        month_start  = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        month_qs     = Order.objects.filter(created_at__gte=month_start)
        month_orders  = month_qs.count()
        month_revenue = month_qs.aggregate(s=Sum("total"))["s"] or Decimal("0.00")

        # Average order value (all time, completed/out for delivery)
        avg_row = Order.objects.filter(
            status__in=[Order.STATUS_COMPLETED, Order.STATUS_OUT_FOR_DELIVERY]
        ).aggregate(avg=Avg("total"))
        avg_order_value = avg_row["avg"] or Decimal("0")

        # Delivery vs collection split today
        delivery_today    = today_qs.filter(delivery_type="delivery").count()
        collection_today  = today_qs.filter(delivery_type="collection").count()

        # Pending (active) orders
        pending_orders = Order.objects.filter(
            status__in=[
                Order.STATUS_PENDING,
                Order.STATUS_CONFIRMED,
                Order.STATUS_PREPARING,
                Order.STATUS_OUT_FOR_DELIVERY,
                Order.STATUS_READY,
            ]
        ).count()

        # Unapproved reviews
        pending_reviews = Review.objects.filter(is_approved=False).count()

        # Registered users (total)
        from django.contrib.auth import get_user_model
        User = get_user_model()
        total_users = User.objects.count()

        # Most-ordered item in the last 30 days
        top_item_row = (
            OrderItem.objects
            .filter(order__created_at__gte=month_ago)
            .values("item_name")
            .annotate(total=Count("id"))
            .order_by("-total")
            .first()
        )
        top_item = top_item_row["item_name"] if top_item_row else None

        # Top 5 items last 30 days for the chart
        top_items_30d = list(
            OrderItem.objects
            .filter(order__created_at__gte=month_ago)
            .values("item_name")
            .annotate(qty=Sum("quantity"))
            .order_by("-qty")[:5]
        )

        # Recent orders (last 6)
        recent_orders = (
            Order.objects
            .select_related("user")
            .order_by("-created_at")[:6]
        )

        # Active promo codes
        active_promos = PromoCode.objects.filter(active=True).order_by("code")

        # Active announcement (if any)
        from .models import SiteAnnouncement
        current_announcement = SiteAnnouncement.objects.filter(is_active=True).first()

        return {
            "stats": {
                "today_orders":      today_orders,
                "today_revenue":     f"{today_revenue:.2f}",
                "week_orders":       week_orders,
                "week_revenue":      f"{week_revenue:.2f}",
                "month_orders":      month_orders,
                "month_revenue":     f"{month_revenue:.2f}",
                "avg_order_value":   f"{avg_order_value:.2f}",
                "pending_orders":    pending_orders,
                "pending_reviews":   pending_reviews,
                "top_item":          top_item,
                "delivery_today":    delivery_today,
                "collection_today":  collection_today,
                "total_users":       total_users,
            },
            "top_items_30d":       top_items_30d,
            "recent_orders":       recent_orders,
            "active_promos":       active_promos,
            "current_announcement": current_announcement,
        }
    except Exception:
        return {}
