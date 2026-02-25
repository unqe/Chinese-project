"""
Auth signals for basket persistence.
When a user logs out we snapshot their basket to UserProfile.saved_basket.
When they log back in we merge it into the current session basket.
"""

import json

from django.contrib.auth.signals import user_logged_in, user_logged_out
from django.dispatch import receiver

from .basket import BASKET_SESSION_KEY


@receiver(user_logged_out)
def save_basket_on_logout(sender, request, user, **kwargs):
    """Persist the session basket to the user's profile so it survives logout."""
    if user is None:
        return
    basket_data = request.session.get(BASKET_SESSION_KEY, {})
    if not basket_data:
        return
    profile = getattr(user, "profile", None)
    if profile is None:
        return
    profile.saved_basket = json.dumps(basket_data)
    profile.save(update_fields=["saved_basket"])


@receiver(user_logged_in)
def restore_basket_on_login(sender, request, user, **kwargs):
    """Merge the saved basket back into the session on login (non-destructive)."""
    profile = getattr(user, "profile", None)
    if not profile or not profile.saved_basket:
        return
    try:
        saved = json.loads(profile.saved_basket)
    except (json.JSONDecodeError, ValueError):
        return
    if not saved:
        return
    current = request.session.get(BASKET_SESSION_KEY, {})
    # Add saved items only if not already in the current basket
    for key, val in saved.items():
        if key not in current:
            current[key] = val
    request.session[BASKET_SESSION_KEY] = current
    request.session.modified = True
    # Clear the stored snapshot so it's not re-applied on next login
    profile.saved_basket = ""
    profile.save(update_fields=["saved_basket"])
