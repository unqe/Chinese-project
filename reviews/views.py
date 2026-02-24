"""
Reviews app views — list, add, edit, and delete reviews.
Supports both logged-in users (linked to account) and
guests who provide their order receipt number + email.
"""

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages

from .models import Review
from .forms import ReviewForm, ReceiptLookupForm
from orders.models import Order


def reviews_list(request):
    """
    Public reviews page. Shows all approved reviews, newest first.
    Calculates average rating in Python to keep the query simple.
    """
    reviews = Review.objects.filter(is_approved=True).select_related("user")
    avg_rating = None
    if reviews.exists():
        total = sum(r.rating for r in reviews)
        avg_rating = round(total / reviews.count(), 1)

    return render(request, "reviews/reviews.html", {
        "reviews": reviews,
        "avg_rating": avg_rating,
        "review_count": reviews.count(),
    })


@login_required
def add_review(request, order_reference):
    """
    Lets a logged-in user review a specific completed order.
    Guards against reviewing someone else's order, non-completed
    orders, and duplicate reviews.
    """
    order = get_object_or_404(Order, reference=order_reference, user=request.user)

    if order.status != Order.STATUS_COMPLETED:
        messages.warning(request, "You can only review completed orders.")
        return redirect("orders:history")

    if hasattr(order, "review"):
        messages.info(request, "You have already reviewed this order.")
        return redirect("reviews:list")

    if request.method == "POST":
        form = ReviewForm(request.POST)
        if form.is_valid():
            review = form.save(commit=False)
            review.user = request.user
            review.order = order
            review.save()
            messages.success(
                request,
                "Thanks for your review! It will appear once our team approves it."
            )
            return redirect("reviews:list")
    else:
        form = ReviewForm()

    return render(request, "reviews/add_review.html", {"form": form, "order": order})


def guest_review(request):
    """
    Two-step guest review form.
    Step 1: Enter receipt reference + email to verify the order is real.
    Step 2: Submit the review content.
    The receipt reference + email are stored in the session between steps.
    """
    # Step 2: review form submission
    if request.method == "POST" and "submit_review" in request.POST:
        ref = request.session.get("guest_review_ref")
        email = request.session.get("guest_review_email")
        if not ref or not email:
            messages.error(request, "Session expired. Please look up your receipt again.")
            return redirect("reviews:guest_review")

        order = get_object_or_404(Order, reference=ref)
        form = ReviewForm(request.POST)
        if form.is_valid():
            review = form.save(commit=False)
            review.user = request.user if request.user.is_authenticated else None
            review.order = order
            review.save()
            # Clear session keys
            request.session.pop("guest_review_ref", None)
            request.session.pop("guest_review_email", None)
            messages.success(
                request,
                "Thanks for your review! It will appear once our team approves it."
            )
            return redirect("reviews:list")
        lookup_form = ReceiptLookupForm()
        return render(request, "reviews/guest_review.html", {
            "lookup_form": lookup_form,
            "review_form": form,
            "order": order,
            "step": 2,
        })

    # Step 1: lookup form submission
    if request.method == "POST":
        lookup_form = ReceiptLookupForm(request.POST)
        if lookup_form.is_valid():
            ref = lookup_form.cleaned_data["reference"].upper().strip()
            email = lookup_form.cleaned_data["email"].lower().strip()
            try:
                order = Order.objects.get(reference=ref)
            except Order.DoesNotExist:
                lookup_form.add_error("reference", "No order found with that reference number.")
                return render(request, "reviews/guest_review.html", {
                    "lookup_form": lookup_form, "step": 1,
                })
            if order.email.lower() != email:
                lookup_form.add_error("email", "Email doesn't match our records for that order.")
                return render(request, "reviews/guest_review.html", {
                    "lookup_form": lookup_form, "step": 1,
                })
            if hasattr(order, "review"):
                messages.info(request, "This order has already been reviewed.")
                return redirect("reviews:list")
            # Verified — store in session and show review form
            request.session["guest_review_ref"] = order.reference
            request.session["guest_review_email"] = email
            return render(request, "reviews/guest_review.html", {
                "lookup_form": ReceiptLookupForm(),
                "review_form": ReviewForm(),
                "order": order,
                "step": 2,
            })
    else:
        lookup_form = ReceiptLookupForm()

    return render(request, "reviews/guest_review.html", {
        "lookup_form": lookup_form,
        "step": 1,
    })


def guest_review_prefill(request, reference):
    """
    Shortcut for guests arriving from the confirmation page.
    Reads the order reference + email from the session so they skip the
    receipt lookup step and land straight on the review form.
    """
    session_ref = request.session.get("last_order_reference")
    if session_ref != reference:
        messages.error(request, "Couldn't verify your order. Please use the receipt lookup form.")
        return redirect("reviews:guest_review")

    order = get_object_or_404(Order, reference=reference, user__isnull=True)

    if order.status != Order.STATUS_COMPLETED:
        messages.info(request, "You can leave a review once your order is completed.")
        return redirect("orders:confirmation", reference=reference)

    if hasattr(order, "review"):
        messages.info(request, "This order has already been reviewed.")
        return redirect("reviews:list")

    # Pre-verify: store in session so the shared guest_review step-2 POST works
    request.session["guest_review_ref"] = order.reference
    request.session["guest_review_email"] = order.email.lower()

    return render(request, "reviews/guest_review.html", {
        "lookup_form": None,
        "review_form": ReviewForm(),
        "order": order,
        "step": 2,
    })


@login_required
def edit_review(request, pk):
    """
    Edit an existing review. Resets approval so the team reviews it again.
    Users can only edit their own reviews.
    """
    review = get_object_or_404(Review, pk=pk, user=request.user)

    if request.method == "POST":
        form = ReviewForm(request.POST, instance=review)
        if form.is_valid():
            updated = form.save(commit=False)
            updated.is_approved = False
            updated.save()
            messages.success(request, "Review updated and sent for re-approval.")
            return redirect("reviews:list")
    else:
        form = ReviewForm(instance=review)

    return render(request, "reviews/edit_review.html", {"form": form, "review": review})


@login_required
def delete_review(request, pk):
    """Deletes the user's own review after a confirmation POST."""
    review = get_object_or_404(Review, pk=pk, user=request.user)

    if request.method == "POST":
        review.delete()
        messages.success(request, "Review deleted.")
        return redirect("reviews:list")

    return render(request, "reviews/delete_review.html", {"review": review})

