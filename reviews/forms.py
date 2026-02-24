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
