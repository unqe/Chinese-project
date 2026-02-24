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
    """
    basket = Basket(request)
    return {
        "basket": basket,
        "basket_count": basket.get_total_quantity(),
        "basket_subtotal": basket.get_subtotal(),
    }
