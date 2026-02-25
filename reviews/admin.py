"""
Reviews app admin configuration.
Admin can approve or reject reviews from the list view, and type
an owner reply that appears publicly under the review.
"""

from django.contrib import admin
from django.utils import timezone
from .models import Review


@admin.register(Review)
class ReviewAdmin(admin.ModelAdmin):
    list_display = ("user", "order", "rating", "title", "is_approved", "has_reply", "created_at")
    list_filter = ("is_approved", "rating", "created_at")
    list_editable = ("is_approved",)
    search_fields = ("user__username", "title", "body")
    readonly_fields = ("user", "order", "created_at", "owner_reply_at")
    ordering = ("-created_at",)
    fieldsets = (
        ("Review", {"fields": ("user", "order", "rating", "title", "body", "is_approved", "created_at")}),
        ("Owner Reply", {"fields": ("owner_reply", "owner_reply_at"), "description": "Write a reply here — it will appear publicly under the review once approved."}),
    )
    actions = ["approve_reviews", "reject_reviews"]

    @admin.display(description="Has reply", boolean=True)
    def has_reply(self, obj):
        return bool(obj.owner_reply)

    def save_model(self, request, obj, form, change):
        """Auto-stamp owner_reply_at when a reply is added/changed."""
        if obj.owner_reply and not obj.owner_reply_at:
            obj.owner_reply_at = timezone.now()
        elif not obj.owner_reply:
            obj.owner_reply_at = None
        super().save_model(request, obj, form, change)

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

