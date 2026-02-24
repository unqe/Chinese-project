"""
Accounts app views — user profile.
"""

from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages

from .forms import UserForm, UserProfileForm


@login_required
def profile(request):
    """
    Profile page where users can update their saved delivery address,
    name, and contact details. Saves both User and UserProfile together.
    """
    if request.method == "POST":
        user_form = UserForm(request.POST, instance=request.user)
        profile_form = UserProfileForm(request.POST, instance=request.user.profile)

        if user_form.is_valid() and profile_form.is_valid():
            user_form.save()
            profile_form.save()
            messages.success(request, "Profile updated successfully.")
            return redirect("accounts:profile")
    else:
        user_form = UserForm(instance=request.user)
        profile_form = UserProfileForm(instance=request.user.profile)

    return render(request, "accounts/profile.html", {
        "user_form": user_form,
        "profile_form": profile_form,
    })

