"""
Orders context processor.
Injects the basket item count into every template so the navbar
basket icon always shows the current number of items.
"""

from .basket import Basket


def basket_context(request):
    """
    Makes 'basket' and 'basket_count' available in every template.
    The Basket object reads from the session, so no database hit occurs.
    Skips gracefully for requests without sessions (e.g. Django admin pages).
    """
    if not hasattr(request, 'session'):
        return {"basket": None, "basket_count": 0, "basket_subtotal": 0}
    basket = Basket(request)
    return {
        "basket": basket,
        "basket_count": basket.get_total_quantity(),
        "basket_subtotal": basket.get_subtotal(),
    }


def announcement_context(request):
    """Injects the latest active SiteAnnouncement into every template.
    Silently returns empty dict on any error so the site never breaks.
    """
    try:
        if not hasattr(request, 'session'):
            return {"site_announcement": None}
        from .models import SiteAnnouncement
        announcement = SiteAnnouncement.objects.filter(is_active=True).first()
        return {"site_announcement": announcement}
    except Exception:
        return {"site_announcement": None}
