"""
Main URL configuration for Despair Chinese.
Routes for all apps, authentication, language switching, and admin.
"""

from django.contrib import admin
from django.urls import path, include
from django.views.generic import TemplateView
from django.conf import settings
from django.conf.urls.static import static
from django.conf.urls.i18n import i18n_patterns

# Custom 403 / 404 handlers (must be at module level, NOT inside i18n_patterns)
handler403 = "despair.views.handler403"
handler404 = "despair.views.handler404"

urlpatterns = [
    # Language switching endpoint used by EN/Chinese toggle in the navbar
    path("i18n/", include("django.conf.urls.i18n")),
]

# i18n_patterns adds /en/ or /zh-hans/ prefix automatically
urlpatterns += i18n_patterns(
    path("kitchen-panel/", admin.site.urls),
    path("accounts/", include("allauth.urls")),
    path("menu/", include("menu.urls", namespace="menu")),
    path("orders/", include("orders.urls", namespace="orders")),
    path("reviews/", include("reviews.urls", namespace="reviews")),
    path("profile/", include("accounts.urls", namespace="accounts")),
    path("terms/", TemplateView.as_view(template_name="pages/terms.html"), name="terms"),
    path("privacy/", TemplateView.as_view(template_name="pages/privacy.html"), name="privacy"),
    # Hidden staff login — separate from the customer login page
    path("staff-access/", TemplateView.as_view(template_name="account/staff_login.html"), name="staff_login"),
    path("", include("menu.urls_home")),
    prefix_default_language=False,
)

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

