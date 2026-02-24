"""
Reviews app views — list, add, edit, and delete reviews.
Only users who have placed a completed order can leave a review.
"""

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages

from .models import Review
from .forms import ReviewForm
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

