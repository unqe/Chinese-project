"""
Management command: update_popular_items

Recalculates which menu items are marked as 'popular' based on how often
they appear in completed orders over the past 90 days.

The top N items (default 8) by order frequency are flagged is_popular=True;
all others are set to False.

Usage:
    python manage.py update_popular_items          # marks top 8
    python manage.py update_popular_items --top 5  # marks top 5
    python manage.py update_popular_items --days 30

Run this from the Heroku scheduler (daily) or call it manually from the
admin shell to refresh badges on the menu.
"""

from django.core.management.base import BaseCommand
from django.db.models import Count
from django.utils import timezone
from datetime import timedelta

from menu.models import MenuItem
from orders.models import OrderItem


class Command(BaseCommand):
    help = "Mark the most-ordered menu items as popular based on recent order data."

    def add_arguments(self, parser):
        parser.add_argument(
            "--top", type=int, default=8,
            help="Number of items to mark as popular (default: 8)."
        )
        parser.add_argument(
            "--days", type=int, default=90,
            help="Look back this many days when counting orders (default: 90)."
        )

    def handle(self, *args, **options):
        top_n = options["top"]
        days = options["days"]
        since = timezone.now() - timedelta(days=days)

        # Count how many order items reference each MenuItem in the window
        top_ids = (
            OrderItem.objects
            .filter(order__created_at__gte=since)
            .values("menu_item_id")
            .annotate(cnt=Count("id"))
            .order_by("-cnt")[:top_n]
            .values_list("menu_item_id", flat=True)
        )
        top_ids = list(top_ids)

        # Mark popular / unpopular
        marked = MenuItem.objects.filter(pk__in=top_ids).update(is_popular=True)
        cleared = MenuItem.objects.exclude(pk__in=top_ids).update(is_popular=False)

        self.stdout.write(
            self.style.SUCCESS(
                f"Updated popular items: {marked} marked popular, {cleared} cleared "
                f"(top {top_n} over last {days} days)."
            )
        )
