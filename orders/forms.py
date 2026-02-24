"""
Orders app forms — checkout and simulated card payment.
"""

from django import forms
from .models import Order


class CheckoutForm(forms.ModelForm):
    """
    Collects contact details, delivery preference, payment method,
    and optional address for delivery orders.
    Card details are fake — for simulation only.
    """

    # Fake card fields — not linked to any model field directly
    card_number = forms.CharField(
        max_length=19,
        required=False,
        widget=forms.TextInput(attrs={
            "placeholder": "1234 5678 9012 3456",
            "class": "form-control card-only",
            "maxlength": "19",
        }),
    )
    card_expiry = forms.CharField(
        max_length=5,
        required=False,
        widget=forms.TextInput(attrs={
            "placeholder": "MM/YY",
            "class": "form-control card-only",
            "maxlength": "5",
        }),
    )
    card_cvv = forms.CharField(
        max_length=4,
        required=False,
        widget=forms.TextInput(attrs={
            "placeholder": "CVV",
            "class": "form-control card-only",
            "maxlength": "4",
        }),
    )

    class Meta:
        model = Order
        fields = [
            "full_name", "email", "phone",
            "delivery_type", "payment_method",
            "address_line1", "address_line2", "city", "postcode",
            "special_instructions",
        ]
        widgets = {
            "full_name": forms.TextInput(attrs={"class": "form-control", "placeholder": "John Smith"}),
            "email": forms.EmailInput(attrs={"class": "form-control", "placeholder": "john@example.com"}),
            "phone": forms.TextInput(attrs={"class": "form-control", "placeholder": "07700 000000"}),
            "delivery_type": forms.RadioSelect(attrs={"class": "form-check-input"}),
            "payment_method": forms.RadioSelect(attrs={"class": "form-check-input"}),
            "address_line1": forms.TextInput(attrs={"class": "form-control delivery-only", "placeholder": "47 Mare Street"}),
            "address_line2": forms.TextInput(attrs={"class": "form-control delivery-only", "placeholder": "Apartment / floor (optional)"}),
            "city": forms.TextInput(attrs={"class": "form-control delivery-only", "placeholder": "London"}),
            "postcode": forms.TextInput(attrs={"class": "form-control delivery-only", "placeholder": "E8 1HE"}),
            "special_instructions": forms.Textarea(attrs={"class": "form-control", "rows": 3, "placeholder": "Any special requests or allergy info..."}),
        }

    def clean(self):
        cleaned_data = super().clean()
        delivery_type = cleaned_data.get("delivery_type")
        payment_method = cleaned_data.get("payment_method")

        # Address is required for delivery orders
        if delivery_type == Order.DELIVERY:
            if not cleaned_data.get("address_line1"):
                self.add_error("address_line1", "Delivery address is required.")
            if not cleaned_data.get("city"):
                self.add_error("city", "City is required.")
            if not cleaned_data.get("postcode"):
                self.add_error("postcode", "Postcode is required.")

        # Fake card validation for simulated card payment
        if payment_method == Order.PAYMENT_CARD:
            card_number = cleaned_data.get("card_number", "").replace(" ", "")
            if not card_number or len(card_number) < 12:
                self.add_error("card_number", "Please enter a valid card number.")
            if not cleaned_data.get("card_expiry"):
                self.add_error("card_expiry", "Please enter the expiry date.")
            if not cleaned_data.get("card_cvv"):
                self.add_error("card_cvv", "Please enter the CVV.")

        return cleaned_data
