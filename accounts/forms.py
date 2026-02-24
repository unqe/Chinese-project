"""
Accounts app forms — user profile editing.
"""

from django import forms
from django.contrib.auth.models import User
from .models import UserProfile


class UserForm(forms.ModelForm):
    """Updates the core User fields (first name, last name, email)."""

    class Meta:
        model = User
        fields = ["first_name", "last_name", "email"]
        widgets = {
            "first_name": forms.TextInput(attrs={"class": "form-control"}),
            "last_name": forms.TextInput(attrs={"class": "form-control"}),
            "email": forms.EmailInput(attrs={"class": "form-control"}),
        }


class UserProfileForm(forms.ModelForm):
    """Updates the extended UserProfile fields (address, phone)."""

    class Meta:
        model = UserProfile
        fields = ["phone", "address_line1", "address_line2", "city", "postcode", "marketing_opt_in"]
        widgets = {
            "phone": forms.TextInput(attrs={"class": "form-control", "placeholder": "07700 000000"}),
            "address_line1": forms.TextInput(attrs={"class": "form-control", "placeholder": "47 Mare Street"}),
            "address_line2": forms.TextInput(attrs={"class": "form-control", "placeholder": "Apartment / floor (optional)"}),
            "city": forms.TextInput(attrs={"class": "form-control", "placeholder": "London"}),
            "postcode": forms.TextInput(attrs={"class": "form-control", "placeholder": "E8 1HE"}),
            "marketing_opt_in": forms.CheckboxInput(attrs={"class": "form-check-input"}),
        }
        labels = {
            "marketing_opt_in": "Send me offers and updates by email",
        }
