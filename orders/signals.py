"""
Auth signals for basket persistence.
When a user logs out we snapshot their basket + promo to UserProfile.saved_basket.
When they log back in we merge it into the current session basket.

Snapshot format (JSON): {"items": {item_id: {...}}, "promo": {"code": "...", "discount": "..."}}
Backward compat: if the root JSON is a flat item dict (old format) we treat it as items only.
"""

import json

from django.contrib.auth.signals import user_logged_in, user_logged_out
from django.dispatch import receiver

from .basket import BASKET_SESSION_KEY, PROMO_SESSION_KEY


def _snapshot_to_profile(user, basket_data, promo_data):
    """Write basket + promo snapshot to the user's profile."""
    profile = getattr(user, "profile", None)
    if profile is None:
        return
    snapshot = {"items": basket_data, "promo": promo_data}
    profile.saved_basket = json.dumps(snapshot)
    try:
        profile.save(update_fields=["saved_basket"])
    except Exception:
        pass  # never crash a request due to profile save failure


def sync_basket_to_profile(request):
    """
    Sync the current session basket + promo to UserProfile.saved_basket.
    Call this after any basket mutation when the user is authenticated so the
    basket is consistent across devices even without an explicit logout.
    """
    user = getattr(request, "user", None)
    if not user or not user.is_authenticated:
        return
    basket_data = request.session.get(BASKET_SESSION_KEY, {})
    promo_data = request.session.get(PROMO_SESSION_KEY, {})
    _snapshot_to_profile(user, basket_data, promo_data)


@receiver(user_logged_out)
def save_basket_on_logout(sender, request, user, **kwargs):
    """Persist the session basket + promo to the user's profile so it survives logout."""
    if user is None or request is None:
        return
    basket_data = request.session.get(BASKET_SESSION_KEY, {})
    promo_data = request.session.get(PROMO_SESSION_KEY, {})
    if not basket_data and not promo_data:
        return
    _snapshot_to_profile(user, basket_data, promo_data)


@receiver(user_logged_in)
def restore_basket_on_login(sender, request, user, **kwargs):
    """Merge the saved basket + promo back into the session on login (non-destructive)."""
    profile = getattr(user, "profile", None)
    if not profile or not profile.saved_basket:
        return
    try:
        raw = json.loads(profile.saved_basket)
    except (json.JSONDecodeError, ValueError):
        return
    if not raw:
        return

    # Support both old format (flat item dict) and new format ({"items": ..., "promo": ...})
    if "items" in raw and isinstance(raw["items"], dict):
        saved_items = raw["items"]
        saved_promo = raw.get("promo", {})
    else:
        saved_items = raw  # old flat format
        saved_promo = {}

    # Merge items: session wins on conflict (don't overwrite what they added before login)
    current_items = request.session.get(BASKET_SESSION_KEY, {})
    for key, val in saved_items.items():
        if key not in current_items:
            current_items[key] = val
    if current_items:
        request.session[BASKET_SESSION_KEY] = current_items

    # Restore promo only if no promo already in session
    if saved_promo and PROMO_SESSION_KEY not in request.session:
        request.session[PROMO_SESSION_KEY] = saved_promo

    request.session.modified = True

    # Clear the stored snapshot so it's not re-applied on subsequent logins
    profile.saved_basket = ""
    try:
        profile.save(update_fields=["saved_basket"])
    except Exception:
        pass
