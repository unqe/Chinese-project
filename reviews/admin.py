"""
Reviews app admin configuration.
Admin can approve or reject reviews from the list view, and type
an owner reply that appears publicly under the review.
"""

from django.contrib import admin
from django.utils import timezone
from django.utils.html import format_html, mark_safe
from .models import Review


@admin.register(Review)
class ReviewAdmin(admin.ModelAdmin):
    change_form_template = "admin/reviews/review_change_form.html"

    list_display = (
        "star_display",
        "review_summary",
        "user",
        "order_link",
        "approval_badge",
        "reply_status",
        "created_at",
    )
    list_filter = ("is_approved", "rating", "created_at")
    search_fields = ("user__username", "title", "body", "order__reference")
    readonly_fields = ("user", "order", "created_at", "owner_reply_at", "review_preview")
    ordering = ("-created_at",)
    date_hierarchy = "created_at"
    fieldsets = (
        (
            "📋 Review Details",
            {
                "fields": ("review_preview", "user", "order", "rating", "title", "body", "is_approved", "created_at"),
                "description": "This is what the customer submitted. Tick <strong>Approved</strong> to make it visible on the public reviews page.",
            },
        ),
        (
            "💬 Owner Reply",
            {
                "fields": ("owner_reply", "owner_reply_at"),
                "description": (
                    "Write your reply below — it will appear publicly under the customer's review. "
                    "The date is stamped automatically when you first save a reply."
                ),
            },
        ),
    )
    actions = ["approve_reviews", "reject_reviews"]

    # ── List display helpers ──────────────────────────────────────────

    @admin.display(description="Rating", ordering="rating")
    def star_display(self, obj):
        stars = "★" * obj.rating + "☆" * (5 - obj.rating)
        colour = {5: "#f0c040", 4: "#d4a017", 3: "#9a8870", 2: "#c0392b", 1: "#922b21"}.get(obj.rating, "#aaa")
        return format_html('<span style="color:{};font-size:1rem;letter-spacing:1px;">{}</span>', colour, stars)

    @admin.display(description="Review")
    def review_summary(self, obj):
        return format_html(
            '<strong style="font-size:0.9rem;">{}</strong><br>'
            '<span style="color:#9a8870;font-size:0.8rem;">{}</span>',
            obj.title,
            (obj.body[:80] + "…") if len(obj.body) > 80 else obj.body,
        )

    @admin.display(description="Order", ordering="order__reference")
    def order_link(self, obj):
        return format_html(
            '<a href="/kitchen-panel/orders/order/{}/change/" style="font-family:monospace;font-size:0.8rem;">{}</a>',
            obj.order.pk,
            obj.order.reference,
        )

    @admin.display(description="Status")
    def approval_badge(self, obj):
        if obj.is_approved:
            return format_html(
                '<span style="background:#1e8449;color:#fff;padding:2px 8px;border-radius:99px;font-size:0.72rem;font-weight:600;">✓ Approved</span>'
            )
        return format_html(
            '<span style="background:#7d6608;color:#f0c040;padding:2px 8px;border-radius:99px;font-size:0.72rem;font-weight:600;">⏳ Pending</span>'
        )

    @admin.display(description="Reply")
    def reply_status(self, obj):
        if obj.owner_reply:
            return format_html(
                '<span style="color:#d4a017;" title="{}"><i class="fas fa-reply"></i> Replied</span>',
                obj.owner_reply[:60],
            )
        return format_html('<span style="color:#555;">—</span>')

    @admin.display(description="Review Preview")
    def review_preview(self, obj):
        """Rich read-only preview shown at the top of the change form fieldset."""
        stars_html = (
            ''.join('<i class="fas fa-star" style="color:#d4a017;"></i>' for _ in range(obj.rating)) +
            ''.join('<i class="far fa-star" style="color:#555;"></i>' for _ in range(5 - obj.rating))
        )
        return format_html(
            '<div style="background:#0d0603;border:1px solid rgba(212,160,23,.25);border-radius:8px;'
            'padding:1.2rem 1.4rem;margin-bottom:.5rem;">'
            '<div style="margin-bottom:.4rem;">{}</div>'
            '<p style="color:#f5f0e8;font-size:1rem;font-weight:600;margin:.4rem 0 .6rem;">&ldquo;{}&rdquo;</p>'
            '<p style="color:#c8bfb0;margin:0;line-height:1.55;">{}</p>'
            '</div>',
            mark_safe(stars_html),
            obj.title,
            obj.body,
        )

    # ── Save hook ─────────────────────────────────────────────────────

    def save_model(self, request, obj, form, change):
        """Auto-stamp owner_reply_at when a reply is added/changed."""
        if obj.owner_reply and not obj.owner_reply_at:
            obj.owner_reply_at = timezone.now()
        elif not obj.owner_reply:
            obj.owner_reply_at = None
        super().save_model(request, obj, form, change)

    # ── Bulk actions ──────────────────────────────────────────────────

    @admin.action(description="✓ Approve selected reviews")
    def approve_reviews(self, request, queryset):
        updated = queryset.update(is_approved=True)
        self.message_user(request, f"{updated} review(s) approved and now visible publicly.")

    @admin.action(description="✗ Reject (hide) selected reviews")
    def reject_reviews(self, request, queryset):
        updated = queryset.update(is_approved=False)
        self.message_user(request, f"{updated} review(s) hidden from the public page.")

