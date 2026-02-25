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
        from reviews.models import Review
        from django.db.models import Sum, Count

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

        return {
            "stats": {
                "today_orders":    today_orders,
                "today_revenue":   f"{today_revenue:.2f}",
                "week_orders":     week_orders,
                "week_revenue":    f"{week_revenue:.2f}",
                "pending_orders":  pending_orders,
                "pending_reviews": pending_reviews,
                "top_item":        top_item,
            }
        }
    except Exception:
        return {}
