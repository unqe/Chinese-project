"""
Accounts app model — UserProfile.
Extends the built-in Django User with extra delivery details.
These are pre-filled at checkout so returning customers don't
have to type their address every time.
"""

from django.db import models
from django.contrib.auth.models import User
from django.db.models.signals import post_save
from django.dispatch import receiver


class UserProfile(models.Model):
    """
    One-to-one extension of the Django User model.
    Stores default delivery address and phone number.
    Created automatically when a new User is registered via the
    post_save signal below.
    """

    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="profile")
    phone = models.CharField(max_length=20, blank=True)
    address_line1 = models.CharField(max_length=200, blank=True)
    address_line2 = models.CharField(max_length=200, blank=True)
    city = models.CharField(max_length=100, blank=True)
    postcode = models.CharField(max_length=10, blank=True)
    marketing_opt_in = models.BooleanField(
        default=False,
        help_text="User agreed to receive promotional emails."
    )
    saved_basket = models.TextField(
        blank=True,
        default="",
        help_text="JSON snapshot of basket saved on logout."
    )
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Profile of {self.user.username}"

    def get_full_address(self):
        """Returns the saved address formatted as a single string."""
        parts = [self.address_line1, self.address_line2, self.city, self.postcode]
        return ", ".join(part for part in parts if part)


@receiver(post_save, sender=User)
def create_or_update_profile(sender, instance, created, **kwargs):
    """
    Signal handler — automatically creates a UserProfile whenever a new
    User account is created, and saves it on subsequent User updates.
    """
    if created:
        UserProfile.objects.create(user=instance)
    else:
        instance.profile.save()

