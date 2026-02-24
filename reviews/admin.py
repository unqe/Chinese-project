"""
Reviews app admin configuration.
Admin can approve or reject reviews from the list view.
"""

from django.contrib import admin
from .models import Review


@admin.register(Review)
class ReviewAdmin(admin.ModelAdmin):
    list_display = ("user", "order", "rating", "title", "is_approved", "created_at")
    list_filter = ("is_approved", "rating", "created_at")
    list_editable = ("is_approved",)
    search_fields = ("user__username", "title", "body")
    readonly_fields = ("user", "order", "created_at")
    ordering = ("-created_at",)
    actions = ["approve_reviews", "reject_reviews"]

    @admin.action(description="Approve selected reviews")
    def approve_reviews(self, request, queryset):
        """Bulk approve reviews from the admin list view."""
        updated = queryset.update(is_approved=True)
        self.message_user(request, f"{updated} review(s) approved.")

    @admin.action(description="Reject selected reviews")
    def reject_reviews(self, request, queryset):
        """Bulk reject (unapprove) reviews."""
        updated = queryset.update(is_approved=False)
        self.message_user(request, f"{updated} review(s) rejected.")

