"""
Reviews app forms.
"""

from django import forms
from .models import Review


class ReviewForm(forms.ModelForm):
    """
    Form for submitting and editing a review.
    Rating is rendered as star radio buttons in the template using
    custom CSS rather than a plain dropdown.
    """

    rating = forms.IntegerField(
        min_value=1,
        max_value=5,
        widget=forms.HiddenInput(),
    )

    class Meta:
        model = Review
        fields = ["rating", "title", "body"]
        widgets = {
            "title": forms.TextInput(attrs={
                "class": "form-control",
                "placeholder": "Summarise your experience...",
            }),
            "body": forms.Textarea(attrs={
                "class": "form-control",
                "rows": 5,
                "placeholder": "Tell others about your order — the food, delivery time, everything!",
            }),
        }


class ReceiptLookupForm(forms.Form):
    """
    Identifies a real order by matching the receipt reference number
    against the email address used at checkout.
    """
    reference = forms.CharField(
        max_length=12,
        widget=forms.TextInput(attrs={
            "class": "form-control",
            "placeholder": "e.g. A3F9B2C1",
            "style": "text-transform:uppercase;letter-spacing:0.1em;",
        }),
        label="Receipt / Order Reference",
    )
    email = forms.EmailField(
        widget=forms.EmailInput(attrs={
            "class": "form-control",
            "placeholder": "Email used at checkout",
        }),
        label="Email Address",
    )
