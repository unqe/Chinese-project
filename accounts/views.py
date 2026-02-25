"""
Accounts app views — user profile.
"""

from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.contrib.auth import logout
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


@login_required
def delete_account(request):
    """GDPR delete-account page. Requires password confirmation.
    On POST with correct password: logs the user out and deletes the account.
    """
    if request.method == "POST":
        password = request.POST.get("password", "")
        user = request.user
        if user.check_password(password):
            logout(request)
            user.delete()
            messages.success(
                request,
                "Your account and all associated data have been permanently deleted.",
            )
            return redirect("menu:menu")
        else:
            messages.error(request, "Incorrect password. Please try again.")
            return redirect("accounts:delete_account")
    return render(request, "accounts/delete_account.html")

