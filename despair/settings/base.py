"""
Base Django settings for Despair Chinese.
Settings shared between development and production.
"""

from pathlib import Path
from decouple import config

# Base directory points to the project root (chinese-project/)
BASE_DIR = Path(__file__).resolve().parent.parent.parent


# ---------------------------------------------------------------------------
# Security
# ---------------------------------------------------------------------------
SECRET_KEY = config("SECRET_KEY", default="change-me-in-production")


# ---------------------------------------------------------------------------
# Application definition
# ---------------------------------------------------------------------------
INSTALLED_APPS = [
    # modeltranslation must come before django.contrib.admin
    "modeltranslation",

    # Jazzmin must come before django.contrib.admin to override the admin UI
    "jazzmin",

    # Django built-ins
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "django.contrib.sites",
    "django.contrib.sitemaps",

    # Third-party
    "allauth",
    "allauth.account",
    "allauth.socialaccount",
    "crispy_forms",
    "crispy_bootstrap5",

    # Cloudinary — media file storage
    "cloudinary_storage",
    "cloudinary",

    # Local apps
    "menu.apps.MenuConfig",
    "orders.apps.OrdersConfig",
    "accounts.apps.AccountsConfig",
    "reviews.apps.ReviewsConfig",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",          # serve static on Heroku
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.locale.LocaleMiddleware",           # language switching
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
    "allauth.account.middleware.AccountMiddleware",
]

ROOT_URLCONF = "despair.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
                "django.template.context_processors.i18n",
                # Custom context processor for basket count & opening hours
                "orders.context_processors.basket_context",
                # Site-wide announcement banner
                "orders.context_processors.announcement_context",
                # Admin dashboard stats (only active on /kitchen-panel/ pages)
                "orders.admin_context.admin_stats",
            ],
        },
    },
]

WSGI_APPLICATION = "despair.wsgi.application"


# ---------------------------------------------------------------------------
# Authentication (django-allauth)
# ---------------------------------------------------------------------------
AUTHENTICATION_BACKENDS = [
    "django.contrib.auth.backends.ModelBackend",
    "allauth.account.auth_backends.AuthenticationBackend",
]

SITE_ID = 1

# Allauth configuration
ACCOUNT_LOGIN_ON_EMAIL_CONFIRMATION = True
ACCOUNT_EMAIL_VERIFICATION = "none"          # no real email server needed
ACCOUNT_LOGIN_METHODS = {"username", "email"}
ACCOUNT_SIGNUP_FIELDS = ["username*", "email*", "password1*", "password2*"]
LOGIN_REDIRECT_URL = "/"
LOGOUT_REDIRECT_URL = "/"

# Session / Remember-me
ACCOUNT_SESSION_REMEMBER = None          # None = respect the "remember me" checkbox
SESSION_COOKIE_AGE = 60 * 60 * 24 * 30  # 30 days when remembered


# ---------------------------------------------------------------------------
# Password validation
# ---------------------------------------------------------------------------
AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]


# ---------------------------------------------------------------------------
# Internationalisation & translations
# ---------------------------------------------------------------------------
LANGUAGE_CODE = "en"

LANGUAGES = [
    ("en", "English"),
    ("zh-hans", "中文"),
]

TIME_ZONE = "Europe/London"
USE_I18N = True
USE_L10N = True
USE_TZ = True

LOCALE_PATHS = [BASE_DIR / "locale"]

# django-modeltranslation — which languages to store in the DB
MODELTRANSLATION_DEFAULT_LANGUAGE = "en"
MODELTRANSLATION_LANGUAGES = ("en", "zh-hans")


# ---------------------------------------------------------------------------
# Cache — DatabaseCache is shared across all gunicorn workers/dynos
# ---------------------------------------------------------------------------
CACHES = {
    "default": {
        "BACKEND": "django.core.cache.backends.db.DatabaseCache",
        "LOCATION": "django_cache",
    }
}

# Static & media files
# ---------------------------------------------------------------------------
STATIC_URL = "/static/"
STATIC_ROOT = BASE_DIR / "staticfiles"
STATICFILES_DIRS = [BASE_DIR / "static"]
STATICFILES_STORAGE = "whitenoise.storage.CompressedStaticFilesStorage"

MEDIA_URL = "/media/"
MEDIA_ROOT = BASE_DIR / "media"

# ---------------------------------------------------------------------------
# Cloudinary media storage
# ---------------------------------------------------------------------------
CLOUDINARY_STORAGE = {
    "CLOUD_NAME": config("CLOUDINARY_CLOUD_NAME", default=""),
    "API_KEY": config("CLOUDINARY_API_KEY", default=""),
    "API_SECRET": config("CLOUDINARY_API_SECRET", default=""),
}
DEFAULT_FILE_STORAGE = "cloudinary_storage.storage.MediaCloudinaryStorage"


# ---------------------------------------------------------------------------
# Default primary key
# ---------------------------------------------------------------------------
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"


# ---------------------------------------------------------------------------
# Crispy forms
# ---------------------------------------------------------------------------
CRISPY_ALLOWED_TEMPLATE_PACKS = "bootstrap5"
CRISPY_TEMPLATE_PACK = "bootstrap5"


# ---------------------------------------------------------------------------
# Jazzmin admin UI configuration
# ---------------------------------------------------------------------------
JAZZMIN_SETTINGS = {
    "site_title": "Despair Chinese",
    "site_header": "🐉 Despair Chinese",
    "site_brand": "Kitchen Panel",
    "site_logo": None,
    "welcome_sign": "Welcome back.",
    "copyright": "Despair Chinese — Hackney, London",
    "search_model": ["auth.User", "menu.MenuItem", "orders.Order"],
    "topmenu_links": [
        {"name": "View Site", "url": "/", "new_window": True},
        {"model": "orders.Order"},
        {"model": "menu.MenuItem"},
        {"model": "reviews.Review"},
    ],
    # ── Sidebar ordering ─────────────────────────────────────────────
    "order_with_respect_to": [
        "orders",
        "menu",
        "reviews",
        "accounts",
        "auth",
        "account",
        "socialaccount",
        "sites",
    ],
    # Hide apps that aren't needed day-to-day
    "hide_apps": ["socialaccount", "sites"],
    "hide_models": [],
    "show_sidebar": True,
    "navigation_expanded": True,
    # ── Icons ─────────────────────────────────────────────────────────
    "icons": {
        "auth":               "fas fa-users-cog",
        "auth.user":          "fas fa-user",
        "auth.Group":         "fas fa-users",
        "menu.Category":      "fas fa-list",
        "menu.MenuItem":      "fas fa-utensils",
        "orders.Order":       "fas fa-shopping-bag",
        "orders.OpeningHours": "fas fa-clock",
        "reviews.Review":     "fas fa-star",
        "account.EmailAddress": "fas fa-envelope",
    },
    "default_icon_parents":  "fas fa-chevron-right",
    "default_icon_children": "fas fa-circle",
    "related_modal_active": False,
    "custom_css": "css/admin_custom.css",
    "custom_js": None,
    "use_google_fonts_cdn": True,
    "show_ui_builder": False,
    "changeform_format": "single",
    "theme": "darkly",
    "dark_mode_theme": "darkly",
    "button_classes": {
        "primary":   "btn-primary",
        "secondary": "btn-secondary",
        "info":      "btn-info",
        "warning":   "btn-warning",
        "danger":    "btn-danger",
        "success":   "btn-success",
    },
}
